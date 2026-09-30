"""ONNX export (doc 122): base model and head as one graph, checked against PyTorch.

The graph is `pixel_values → base model → the app's token split → head → outputs`, with a
fixed input size (the grid is part of the graph) and a dynamic batch. onnxruntime runs it
once at export time; the largest difference to PyTorch goes into the card, and above
MAX_DIFF the export is refused.
"""

from __future__ import annotations

import importlib.util
import logging
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

OPSET = 18
MAX_DIFF = 1e-3


def onnx_missing() -> str | None:
    """Why ONNX cannot be exported here, or None when it can."""
    for package in ("onnx", "onnxruntime"):
        if importlib.util.find_spec(package) is None:
            return f"'{package}' is not installed: pip install '.[export]'"
    return None


def export_head_onnx(instance: Any, size: int) -> tuple[bytes, dict[str, Any]]:
    """(model.onnx bytes, the card's `onnx` section) for a trained head."""
    import numpy as np
    import onnxruntime as ort
    import torch
    from safetensors.torch import load_file
    from torch import nn
    from transformers import AutoModel

    from app.core.paths import resolve_model_dir
    from app.ml.backbone import BackboneFeatures, _split_tokens, read_capabilities
    from app.ml.heads.builders import build_head

    caps = read_capabilities(instance.backbone_id)
    # A CPU copy of its own: the app's cached backbone stays where inference uses it.
    model = AutoModel.from_pretrained(str(resolve_model_dir(instance.backbone_id))).eval()
    head = build_head(instance.head_type_id, caps, instance.num_classes)
    head.load_state_dict(load_file(instance.weights_path))
    grid = (size // caps.patch_size, size // caps.patch_size)

    class Whole(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.model, self.head = model, head.eval()

        def forward(self, pixel_values: torch.Tensor) -> tuple[torch.Tensor, ...]:
            hidden = self.model(pixel_values=pixel_values).last_hidden_state
            cls, patches = _split_tokens(hidden, caps.num_prefix_tokens, grid)
            out = self.head(BackboneFeatures(cls=cls, patches=patches, grid=grid))
            return tuple(out[key] for key in sorted(out))

    whole = Whole().eval()
    sample = torch.randn(1, 3, size, size)
    with torch.no_grad():
        reference = whole(sample)
        names = sorted(
            head(
                BackboneFeatures(
                    cls=torch.zeros(1, caps.embed_dim),
                    patches=torch.zeros(1, caps.embed_dim, *grid),
                    grid=grid,
                )
            )
        )
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "model.onnx"
        torch.onnx.export(
            whole,
            (sample,),
            str(path),
            input_names=["pixel_values"],
            output_names=names,
            dynamic_axes={"pixel_values": {0: "batch"}, **{n: {0: "batch"} for n in names}},
            opset_version=OPSET,
            dynamo=False,
        )
        data = path.read_bytes()
        session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
        outputs = session.run(None, {"pixel_values": sample.numpy()})
    diff = max(float(np.abs(o - r.numpy()).max()) for o, r in zip(outputs, reference, strict=True))
    if diff > MAX_DIFF:
        raise ValueError(
            f"ONNX differs from PyTorch by {diff:.2e} (limit {MAX_DIFF:.0e}); not exported."
        )
    logger.info("Exported %s to ONNX (%d MB, max diff %.2e)", instance.id, len(data) // 2**20, diff)
    return data, {
        "file": "model.onnx",
        "input": {"name": "pixel_values", "shape": ["batch", 3, size, size], "dtype": "float32"},
        "outputs": [
            {"name": name, "shape": ["batch", *out.shape[1:]]}
            for name, out in zip(names, outputs, strict=True)
        ],
        "opset": OPSET,
        "exporter": "torch.onnx (TorchScript)",
        "max_abs_diff": diff,
        "note": "Preprocess as in `preprocessing`; decode as in `outputs.decode`.",
    }


__all__ = ["MAX_DIFF", "OPSET", "export_head_onnx", "onnx_missing"]

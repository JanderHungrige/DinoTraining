"""ONNX export (doc 122), end to end on a tiny real DINOv2 built from a config."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from app.ml.backbone import BackboneCapabilities
from app.ml.heads.builders import build_head
from app.mlops import onnx_export
from app.mlops.onnx_export import export_head_onnx, onnx_missing

pytest.importorskip("onnxruntime")
SIZE = 56
CAPS = BackboneCapabilities("tiny-dino", "dinov2", 14, 32, 1, 1, SIZE)


@pytest.fixture
def tiny(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    from safetensors.torch import save_file
    from transformers import Dinov2Config, Dinov2Model

    config = Dinov2Config(
        hidden_size=32,
        num_hidden_layers=1,
        num_attention_heads=2,
        intermediate_size=64,
        patch_size=14,
        image_size=SIZE,
    )
    Dinov2Model(config).save_pretrained(tmp_path / "tiny-dino")
    monkeypatch.setattr("app.ml.backbone.read_capabilities", lambda _id: CAPS)
    monkeypatch.setattr("app.core.paths.resolve_model_dir", lambda _id: tmp_path / "tiny-dino")
    head = build_head("dense-detector", CAPS, 3)
    save_file(
        {k: v.contiguous() for k, v in head.state_dict().items()},
        str(tmp_path / "head.safetensors"),
    )
    return SimpleNamespace(
        id="h1",
        backbone_id="tiny-dino",
        head_type_id="dense-detector",
        num_classes=3,
        weights_path=str(tmp_path / "head.safetensors"),
    )


def test_the_packages_are_there_for_this_build() -> None:
    assert onnx_missing() is None


def test_one_graph_that_matches_pytorch(tiny: SimpleNamespace, tmp_path: Path) -> None:
    import onnxruntime as ort

    data, section = export_head_onnx(tiny, SIZE)
    assert section["input"] == {
        "name": "pixel_values",
        "shape": ["batch", 3, SIZE, SIZE],
        "dtype": "float32",
    }
    assert [o["name"] for o in section["outputs"]] == sorted(o["name"] for o in section["outputs"])
    assert section["max_abs_diff"] < 1e-4
    path = tmp_path / "model.onnx"
    path.write_bytes(data)
    session = ort.InferenceSession(str(path))
    # The batch really is dynamic: two pictures at once.
    outputs = session.run(
        None, {"pixel_values": np.random.rand(2, 3, SIZE, SIZE).astype(np.float32)}
    )
    assert all(out.shape[0] == 2 for out in outputs)


def test_refused_above_the_limit(tiny: SimpleNamespace, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(onnx_export, "MAX_DIFF", -1.0)
    with pytest.raises(ValueError, match="not exported"):
        export_head_onnx(tiny, SIZE)


def test_the_app_s_cached_backbone_is_not_touched(tiny: SimpleNamespace) -> None:
    """The export loads a CPU copy of its own; nothing is moved off the app's device."""
    from app.ml import backbone

    before = dict(backbone._cache) if hasattr(backbone, "_cache") else {}
    export_head_onnx(tiny, SIZE)
    after = dict(backbone._cache) if hasattr(backbone, "_cache") else {}
    assert before.keys() == after.keys()
    assert torch.get_default_dtype() == torch.float32

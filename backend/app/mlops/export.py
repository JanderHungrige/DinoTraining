"""Export bundles (doc 121): a zip that runs a trained model outside the app.

The zip never holds a local path or a secret; an export is a copy and changes nothing in
the library; `.pt` weights are read with `weights_only=True` so exporting never runs
pickled code.
"""

from __future__ import annotations

import io
import json
import logging
import re
import zipfile
from pathlib import Path

from app.ml.foundation.instances import FoundationInstanceStore
from app.ml.heads.store import HeadInstanceStore
from app.mlops.card import card_for
from app.mlops.export_texts import PREDICT_PY, finetuned_readme, head_readme, requirements
from app.mlops.onnx_export import export_head_onnx, onnx_missing
from app.mlops.runtime_source import SUPPORTED, runtime_source

logger = logging.getLogger(__name__)


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("._") or "model"


def model_folder(kind: str, instance_id: str) -> Path:
    """Where the model lives, for "Show where it is"."""
    if kind == "heads":
        return Path(HeadInstanceStore().get(instance_id).weights_path).parent
    if kind == "finetuned":
        store = FoundationInstanceStore()
        if store.get(instance_id) is None:
            raise LookupError(f"No such fine-tuned model: {instance_id}")
        return store.directory(instance_id)
    raise LookupError(f"Unknown model kind: {kind}")


def _as_safetensors(path: Path) -> tuple[str, bytes]:
    """A `.pt` state dict as safetensors bytes; anything else as it is."""
    if path.suffix != ".pt":
        return path.name, path.read_bytes()
    import torch
    from safetensors.torch import save

    state = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(state, dict):
        return path.name, path.read_bytes()
    tensors = {k: v.contiguous() for k, v in state.items() if isinstance(v, torch.Tensor)}
    return path.with_suffix(".safetensors").name, save(tensors)


def _onnx(instance: object, card: dict[str, object], files: dict[str, bytes]) -> None:
    """Add model.onnx and the card's `onnx` section, or say in the card why not."""
    missing = onnx_missing()
    if missing:
        card["onnx"] = {"note": missing}
        return
    size = int(card["preprocessing"]["size"])  # type: ignore[index]
    try:
        files["model.onnx"], card["onnx"] = export_head_onnx(instance, size)
    except (ValueError, RuntimeError) as error:
        logger.warning("ONNX export failed: %s", error)
        card["onnx"] = {"note": f"not exported: {error}"}


def bundle_files(kind: str, instance_id: str, onnx: bool = True) -> tuple[str, dict[str, bytes]]:
    """(zip name, file name → bytes) for one model."""
    card = card_for(kind, instance_id)
    name = _safe_name(str(card["model"]["name"]))
    files: dict[str, bytes] = {}
    if kind == "heads":
        weights = Path(HeadInstanceStore().get(instance_id).weights_path)
        files["head.safetensors"] = weights.read_bytes()
        card["weights"][0]["file"] = "head.safetensors"
        runnable = card["head"]["type_id"] in SUPPORTED and "size" in card["preprocessing"]
        if runnable and onnx:
            _onnx(HeadInstanceStore().get(instance_id), card, files)
        if runnable:
            files["dino_runtime.py"] = runtime_source().encode()
            files["predict.py"] = PREDICT_PY.encode()
            files["requirements.txt"] = requirements().encode()
        files["README.md"] = head_readme(card, runnable).encode()
    else:
        card["onnx"] = {"note": "fine-tuned models are exported as weights; see doc 122"}
        directory = model_folder(kind, instance_id)
        for entry in card["weights"]:
            file_name, data = _as_safetensors(directory / entry["file"])
            files[file_name] = data
            entry["file"] = file_name
        files["README.md"] = finetuned_readme(card).encode()
    files["model.json"] = json.dumps(card, indent=2).encode()
    return f"{name}.zip", files


def zip_bytes(files: dict[str, bytes]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for file_name, data in sorted(files.items()):
            archive.writestr(file_name, data)
    return buffer.getvalue()


def export_to(kind: str, instance_id: str, destination: Path, onnx: bool = True) -> Path:
    """Write the bundle into an existing folder; returns the zip's path."""
    if not destination.is_absolute() or not destination.is_dir():
        raise ValueError(f"Not a folder to export into: {destination}")
    zip_name, files = bundle_files(kind, instance_id, onnx)
    target = destination / zip_name
    target.write_bytes(zip_bytes(files))
    logger.info("Exported %s %s to %s", kind, instance_id, target)
    return target


def export_payload(kind: str, instance_id: str, onnx: bool = True) -> tuple[str, bytes]:
    zip_name, files = bundle_files(kind, instance_id, onnx)
    return zip_name, zip_bytes(files)


__all__ = ["bundle_files", "export_payload", "export_to", "model_folder", "zip_bytes"]

"""Which adapter trains which fine-tunable model (doc 93). One line per model."""

from __future__ import annotations

from app.finetune.adapter import FinetuneAdapter
from app.finetune.adapters.backbone import BackboneAdapter
from app.finetune.adapters.rfdetr import RfDetrAdapter
from app.finetune.adapters.sam2 import Sam2Adapter


def get_adapter(finetune_id: str) -> FinetuneAdapter:
    if finetune_id.startswith("rf-detr"):
        return RfDetrAdapter(finetune_id)
    if finetune_id.startswith("sam2"):
        return Sam2Adapter(finetune_id)
    for task in ("classification", "segmentation"):
        suffix = f"-{task}"
        if finetune_id.startswith(("dinov2", "dinov3")) and finetune_id.endswith(suffix):
            return BackboneAdapter(finetune_id, finetune_id.removesuffix(suffix), task)
    raise LookupError(f"No training adapter for {finetune_id} yet")


__all__ = ["get_adapter"]

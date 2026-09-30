"""The parameter catalogue (doc 99): every training knob a model honours, explained once."""

from __future__ import annotations

from app.params.finetune import BACKBONE, RF_DETR
from app.params.heads import HEAD
from app.params.sam import SAM2, SAM3
from app.params.spec import Choice, Parameter, ParameterSet, Value

FAMILIES: tuple[ParameterSet, ...] = (HEAD, RF_DETR, SAM2, SAM3, BACKBONE)
_BY_FAMILY = {family.family: family for family in FAMILIES}


def family_for(model_id: str) -> ParameterSet:
    """The family a model id belongs to, matched like `get_adapter` (doc 93)."""
    if model_id in _BY_FAMILY:
        return _BY_FAMILY[model_id]
    if model_id.startswith("rf-detr"):
        return RF_DETR
    if model_id.startswith("sam2"):
        return SAM2
    if model_id == "sam3":
        return SAM3
    if model_id.startswith(("dinov2", "dinov3")) and model_id.endswith(
        ("-classification", "-segmentation")
    ):
        return BACKBONE
    raise LookupError(f"No training parameters for {model_id}")


__all__ = ["FAMILIES", "Choice", "Parameter", "ParameterSet", "Value", "family_for"]

"""Model cards (doc 120): everything an application needs to use a trained model.

Built from the stored record, never typed by hand. The export bundle (doc 121), the ONNX
file (doc 122) and MLflow (docs 123, 124) all carry this one description.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app import __version__
from app.ml.foundation.instances import FoundationInstance, FoundationInstanceStore
from app.ml.heads.instances import HeadInstance
from app.ml.heads.registry import get_head_type
from app.ml.heads.store import HeadInstanceStore
from app.mlops.card_parts import (
    OUTPUTS,
    base_block,
    datasets_block,
    features_block,
    history_block,
    preprocessing_block,
    recipe_block,
    weights_block,
)

CARD_SCHEMA = "dinotraining.model-card/1"


def _head_module(instance: HeadInstance) -> str | None:
    """The head's module class, as `build_head` constructs it for this backbone."""
    try:
        from app.ml.backbone import read_capabilities
        from app.ml.heads.builders import build_head

        caps = read_capabilities(instance.backbone_id)
        return type(build_head(instance.head_type_id, caps, instance.num_classes)).__name__
    except (LookupError, ValueError, OSError):
        return None


def head_card(instance: HeadInstance) -> dict[str, Any]:
    spec = get_head_type(instance.head_type_id)
    if spec is None:
        raise LookupError(f"Unknown head type: {instance.head_type_id}")
    config = instance.config
    recipe_id = config.get("recipe_id")
    return {
        "schema": CARD_SCHEMA,
        "model": {
            "id": instance.id,
            "name": instance.name,
            "kind": "head",
            "origin": instance.kind,
            "source_repo": instance.source_repo,
            "created_at": instance.created_at,
            "app_version": __version__,
        },
        "task": instance.task,
        "base": base_block(instance.backbone_id),
        "head": {
            "type_id": spec.id,
            "title": spec.title,
            "consumes": spec.consumes,
            "module": _head_module(instance),
            "num_classes": instance.num_classes,
        },
        "classes": list(instance.class_names),
        "preprocessing": preprocessing_block(instance.backbone_id, spec),
        "features": features_block(spec.consumes),
        "outputs": {"decode": OUTPUTS.get(instance.task, "see the app's inference engine")},
        "metrics": {
            "values": instance.metrics,
            "primary": instance.primary_metric,
            "primary_value": instance.primary_metric_value,
        },
        "training": {
            "epochs": instance.epochs_trained,
            "best_epoch": instance.best_epoch,
            "datasets": datasets_block(instance.dataset_ids),
            "recipe": recipe_block(instance.dataset_ids, str(recipe_id) if recipe_id else None),
            "settings": config,
            **history_block(instance.history),
        },
        "weights": weights_block([Path(instance.weights_path)]),
    }


def finetuned_card(instance: FoundationInstance, directory: Path) -> dict[str, Any]:
    weights = sorted(p for p in directory.iterdir() if p.is_file() and p.name != "instance.json")
    return {
        "schema": CARD_SCHEMA,
        "model": {
            "id": instance.id,
            "name": instance.name,
            "kind": "finetuned",
            "finetune_id": instance.finetune_id,
            "created_at": instance.created_at,
            "app_version": __version__,
        },
        "task": _finetune_task(instance.finetune_id),
        "base": base_block(instance.base_model_id),
        "weights_kind": instance.weights_kind,
        "classes": list(instance.class_names),
        "preprocessing": {"note": f"the base model's own processor ({instance.base_model_id})"},
        "metrics": {"values": instance.metrics, "baseline": instance.baseline_metrics},
        "training": {
            "epochs": instance.epochs_trained,
            "datasets": datasets_block(instance.dataset_ids),
            "recipe": recipe_block(instance.dataset_ids, instance.recipe_id),
            "settings": instance.parameters,
            **history_block(instance.history),
        },
        "weights": weights_block(weights),
    }


def _finetune_task(finetune_id: str) -> str:
    try:
        from app.finetune.requirements import get_requirements

        return get_requirements(finetune_id).task
    except LookupError:
        return "unknown"


def card_for(kind: str, instance_id: str) -> dict[str, Any]:
    """The card of a stored head (`heads`) or fine-tuned model (`finetuned`)."""
    if kind == "heads":
        return head_card(HeadInstanceStore().get(instance_id))
    if kind == "finetuned":
        store = FoundationInstanceStore()
        instance = store.get(instance_id)
        if instance is None:
            raise LookupError(f"No such fine-tuned model: {instance_id}")
        return finetuned_card(instance, store.directory(instance_id))
    raise LookupError(f"Unknown model kind: {kind}")


__all__ = ["CARD_SCHEMA", "card_for", "finetuned_card", "head_card"]

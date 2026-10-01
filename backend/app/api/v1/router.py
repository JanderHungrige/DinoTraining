"""Aggregate router for /api/v1.

Every v1 feature router is included here, and nowhere else. Adding a route means
adding one line to this file — that is what keeps the surface auditable.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    agent_docs,
    annotate,
    annotation_targets,
    annotators,
    backbones,
    dataset_classes,
    dataset_examples,
    dataset_exchange,
    dataset_image_masks,
    dataset_images,
    dataset_import,
    dataset_phrases,
    dataset_quality,
    datasets,
    exports,
    finetune_jobs,
    finetune_requirements,
    foundation,
    foundation_finetune,
    generate,
    generate_foundation,
    head_catalog,
    head_types,
    heads,
    health,
    inference,
    mlops,
    model_cards,
    model_exports,
    models,
    prep_audit,
    prep_augment,
    prep_balance,
    prep_default_recipe,
    prep_fixes,
    prep_input,
    prep_intake,
    prep_recipes,
    prep_split,
    prescan,
    segment,
    settings,
    system,
    training,
    training_parameters,
    video,
    video_extract,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent_docs.router, tags=["docs"])
api_router.include_router(annotate.router, tags=["annotate"])
api_router.include_router(annotators.router, tags=["annotators"])
api_router.include_router(models.router, tags=["models"])
api_router.include_router(backbones.router, tags=["backbones"])
api_router.include_router(head_types.router, tags=["heads"])
api_router.include_router(heads.router, tags=["heads"])
api_router.include_router(head_catalog.router, tags=["heads"])
api_router.include_router(inference.router, tags=["inference"])
api_router.include_router(foundation.router, tags=["foundation"])
api_router.include_router(foundation_finetune.router, tags=["foundation"])
api_router.include_router(training.router, tags=["training"])
api_router.include_router(training_parameters.router, tags=["training"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(settings.router, tags=["settings"])
# Doc 136: before `datasets`, whose GET /datasets/{dataset_id} would take /datasets/profiles.
api_router.include_router(dataset_import.router, tags=["datasets"])
# Before datasets.router too: /datasets/examples is not a dataset id (doc 138).
api_router.include_router(dataset_examples.router, tags=["datasets"])
api_router.include_router(dataset_exchange.router, tags=["datasets"])
api_router.include_router(exports.router, tags=["datasets"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(dataset_classes.router, tags=["datasets"])
api_router.include_router(dataset_image_masks.router, tags=["datasets"])
api_router.include_router(dataset_phrases.router, tags=["datasets"])
api_router.include_router(annotation_targets.router, tags=["datasets"])
api_router.include_router(segment.router, tags=["annotation"])
api_router.include_router(dataset_quality.router, tags=["datasets"])
api_router.include_router(dataset_images.router, tags=["datasets"])
api_router.include_router(generate.router, tags=["generate"])
api_router.include_router(generate_foundation.router, tags=["generate"])
api_router.include_router(prescan.router, tags=["generate"])
api_router.include_router(video.router, tags=["video"])
api_router.include_router(video_extract.router, tags=["video"])
api_router.include_router(prep_audit.router, tags=["prepare-data"])
api_router.include_router(prep_intake.router, tags=["prepare-data"])
api_router.include_router(prep_fixes.router, tags=["prepare-data"])
api_router.include_router(prep_split.router, tags=["prepare-data"])
api_router.include_router(prep_input.router, tags=["prepare-data"])
api_router.include_router(prep_balance.router, tags=["prepare-data"])
api_router.include_router(prep_augment.router, tags=["prepare-data"])
api_router.include_router(prep_default_recipe.router, tags=["prepare-data"])
api_router.include_router(prep_recipes.router, tags=["prepare-data"])
api_router.include_router(finetune_requirements.router, tags=["fine-tuning"])
api_router.include_router(finetune_jobs.router, tags=["fine-tuning"])
api_router.include_router(model_cards.router, tags=["mlops"])
api_router.include_router(model_exports.router, tags=["mlops"])
api_router.include_router(mlops.router, tags=["mlops"])

"""Aggregate router for /api/v1.

Every v1 feature router is included here, and nowhere else. Adding a route means
adding one line to this file — that is what keeps the surface auditable.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    annotate,
    annotators,
    backbones,
    datasets,
    foundation,
    foundation_finetune,
    generate,
    generate_foundation,
    head_catalog,
    head_types,
    heads,
    health,
    inference,
    models,
    prescan,
    settings,
    system,
    training,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
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
api_router.include_router(system.router, tags=["system"])
api_router.include_router(settings.router, tags=["settings"])
api_router.include_router(datasets.router, tags=["datasets"])
api_router.include_router(generate.router, tags=["generate"])
api_router.include_router(generate_foundation.router, tags=["generate"])
api_router.include_router(prescan.router, tags=["generate"])

"""Aggregate router for /api/v1.

Every v1 feature router is included here, and nowhere else. Adding a route means
adding one line to this file — that is what keeps the surface auditable.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import annotate, backbones, datasets, head_types, health, models, system

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(annotate.router, tags=["annotate"])
api_router.include_router(models.router, tags=["models"])
api_router.include_router(backbones.router, tags=["backbones"])
api_router.include_router(head_types.router, tags=["heads"])
api_router.include_router(system.router, tags=["system"])
api_router.include_router(datasets.router, tags=["datasets"])

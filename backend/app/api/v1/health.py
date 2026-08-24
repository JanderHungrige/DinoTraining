"""Readiness endpoint.

The Tauri shell polls this after spawning the sidecar and only shows the window's
content once it answers. Keep it cheap and dependency-free — it must respond while
models are still downloading.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app import __version__
from app.core.config import Device, get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Contract mirrored by ``HealthResponse`` in apps/frontend/src/api/types.ts."""

    status: Literal["ok"] = Field(description="Literal 'ok'; anything else means not-ready.")
    version: str = Field(description="Backend package version.")
    device: Device = Field(description="Resolved compute device — never 'auto'.")
    api_prefix: str = Field(description="Configured API prefix, echoed for client assertion.")


@router.get("/health", response_model=HealthResponse, summary="Sidecar readiness probe")
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(
        status="ok",
        version=__version__,
        device=settings.resolved_device,
        api_prefix=settings.api_prefix,
    )

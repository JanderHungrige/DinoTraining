"""System information for the Admin tab: device, cache location, disk, token presence."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import Device, get_settings
from app.core.paths import free_disk_bytes, model_cache_root

router = APIRouter()

_BYTES_PER_MB = 1024 * 1024


class SystemInfo(BaseModel):
    device: Device = Field(description="Resolved compute device — never 'auto'.")
    cache_dir: str = Field(description="Where model weights are stored.")
    hf_token_present: bool = Field(
        description="Whether a HuggingFace token is configured. Never the token itself."
    )
    free_disk_mb: int


@router.get("/system/info", response_model=SystemInfo, summary="Device, cache and disk status")
async def system_info() -> SystemInfo:
    settings = get_settings()
    cache_dir = model_cache_root(settings)
    return SystemInfo(
        device=settings.resolved_device,
        cache_dir=str(cache_dir),
        # Presence only. The token itself never crosses this boundary.
        hf_token_present=settings.hf_token is not None,
        free_disk_mb=free_disk_bytes(cache_dir) // _BYTES_PER_MB,
    )

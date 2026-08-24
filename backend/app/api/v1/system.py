"""System information for the Admin tab: device, cache location, disk, token, GPU."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import Device, get_settings
from app.core.paths import free_disk_bytes, model_cache_root
from app.ml.accelerator import report as accelerator_report

router = APIRouter()

_BYTES_PER_MB = 1024 * 1024


class SystemInfo(BaseModel):
    device: Device = Field(description="Resolved compute device — never 'auto'.")
    cache_dir: str = Field(description="Where model weights are stored.")
    hf_token_present: bool = Field(
        description="Whether a HuggingFace token is configured. Never the token itself."
    )
    free_disk_mb: int


class GpuInfo(BaseModel):
    name: str
    memory_mb: int
    driver_version: str


class AcceleratorInfo(BaseModel):
    """What this machine could use, versus what this build can (doc 57)."""

    device: str
    #: The torch build frozen into this sidecar — `cpu`, `cuda`, `mps`, `rocm`.
    torch_variant: str
    nvidia: list[GpuInfo]
    #: True when NVIDIA hardware is present and this build cannot use it. **The only
    #: actionable state**, and the one the Admin panel acts on.
    upgrade_available: bool
    #: Set when a driver is installed but did not answer — a different problem from having
    #: no GPU, and it needs a different fix.
    driver_error: str | None
    summary: str


@router.get(
    "/system/accelerator",
    response_model=AcceleratorInfo,
    summary="GPU hardware present, and whether this build can use it",
)
async def accelerator() -> AcceleratorInfo:
    """Asks the **driver**, not torch.

    A CPU-only build reports `torch.cuda.is_available() == False` on a machine with four
    A100s, so torch cannot answer "is there a GPU here". `nvidia-smi` can, and it ships
    with the driver.
    """
    found = accelerator_report(str(get_settings().resolved_device))
    return AcceleratorInfo(
        device=found.device,
        torch_variant=found.torch_variant,
        nvidia=[
            GpuInfo(name=gpu.name, memory_mb=gpu.memory_mb, driver_version=gpu.driver_version)
            for gpu in found.nvidia
        ],
        upgrade_available=found.upgrade_available,
        driver_error=found.driver_error,
        summary=found.summary,
    )


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

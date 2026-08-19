"""Application settings.

Every module reads configuration through :func:`get_settings` — never ``os.environ``
directly. That is how one setting quietly ends up meaning two different things.
"""

from __future__ import annotations

from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env_file import env_file_path

Device = Literal["cuda", "mps", "cpu"]

_VALID_DEVICES = frozenset({"auto", "cuda", "mps", "cpu"})


def resolve_device(requested: str) -> Device:
    """Turn a configured device string into a concrete device.

    ``auto`` picks the best available backend (CUDA → MPS → CPU). An *explicit*
    device that is unavailable raises: the user asked for that device, so silently
    downgrading them to CPU and letting them wonder why training crawls is worse
    than failing at startup.
    """
    device = requested.strip().lower()
    if device not in _VALID_DEVICES:
        raise ValueError(
            f"Unknown device {requested!r}. Expected one of: {', '.join(sorted(_VALID_DEVICES))}"
        )

    import torch

    cuda_ready = torch.cuda.is_available()
    mps_ready = torch.backends.mps.is_available()

    if device == "auto":
        if cuda_ready:
            return "cuda"
        return "mps" if mps_ready else "cpu"

    if device == "cuda" and not cuda_ready:
        raise RuntimeError(
            "DINO_DEVICE=cuda but no CUDA device is available. "
            "Set DINO_DEVICE=auto to fall back automatically."
        )
    if device == "mps" and not mps_ready:
        raise RuntimeError(
            "DINO_DEVICE=mps but Apple MPS is not available. "
            "Set DINO_DEVICE=auto to fall back automatically."
        )
    return device  # type: ignore[return-value]


class Settings(BaseSettings):
    """Backend configuration, loaded from the environment and ``.env``."""

    # No env_file here on purpose. A bare ``Settings()`` reads the environment only,
    # which is what keeps a test run away from the developer's real credentials; the
    # file is supplied by get_settings() below, at call time.
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # --- HuggingFace ---
    hf_token: SecretStr | None = Field(default=None, alias="HF_TOKEN")
    model_cache_dir: Path | None = Field(default=None, alias="DINO_MODEL_CACHE_DIR")

    # --- API ---
    api_host: str = Field(default="127.0.0.1", alias="DINO_API_HOST")
    api_port: int = Field(default=8756, alias="DINO_API_PORT")
    api_prefix: str = Field(default="/api/v1", alias="DINO_API_PREFIX")

    # --- Compute ---
    device: str = Field(default="auto", alias="DINO_DEVICE")

    # --- Datasets ---
    data_dir: Path | None = Field(default=None, alias="DINO_DATA_DIR")

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("hf_token", "model_cache_dir", "data_dir", mode="before")
    @classmethod
    def _blank_is_unset(cls, value: Any) -> Any:
        """`.env` templates ship keys with empty values; treat those as absent."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @cached_property
    def resolved_device(self) -> Device:
        """The concrete device this process will use. Never ``auto``."""
        return resolve_device(self.device)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings, loaded once.

    The ``.env`` path is resolved *here* rather than in ``model_config``, for two reasons.
    It must be absolute — a relative ".env" resolves against the working directory, so a
    backend started from ``backend/`` looked for ``backend/.env``, found nothing, and ran
    on defaults while the real file sat at the repository root, saying nothing. And it must
    be resolved per call, so that clearing this cache after the token is written picks the
    new value up without a restart — uvicorn does not reload.
    """
    return Settings(_env_file=env_file_path())

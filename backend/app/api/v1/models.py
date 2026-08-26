"""Model catalogue, downloads and removal.

Two rules shape every handler here: a request names a *registry key*, never a
HuggingFace repo; and every path is confined to the cache root before it is touched.
"""

from __future__ import annotations

import logging
import shutil
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.paths import (
    PathConfinementError,
    directory_size_bytes,
    is_installed,
    model_cache_root,
    resolve_model_dir,
)
from app.ml.downloads import DownloadJob, get_download_manager
from app.ml.registry import (
    REDISTRIBUTION_NOTES,
    ModelFamily,
    ModelKind,
    ModelSpec,
    all_models,
    get_model,
    licence_url,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_BYTES_PER_MB = 1024 * 1024


class ModelInfo(BaseModel):
    id: str
    repo_id: str
    # Imported from the registry, never re-declared. A local copy of these literals is how
    # adding a model family 500s this endpoint and blanks the admin tab: the catalogue and
    # its response schema drift, and nothing fails until a new entry is served.
    kind: ModelKind
    family: ModelFamily
    gated: bool
    approx_size_mb: int
    description: str
    licence: str
    licence_url: str
    #: True when a token alone is not enough and access must also be granted. SAM 3 only.
    requires_access_request: bool
    #: True when the licence forbids commercial use, so the admin panel can say so
    #: *before* the download rather than after. See `35-model-licence-surfacing`.
    non_commercial: bool
    #: Part of the set a first run needs (doc 65). Surfaced so the admin panel can offer
    #: them together rather than making a new user work out which five of fifteen matter.
    starter: bool = False
    #: What redistributing this app with the model installed obliges (doc 54).
    redistribution: str
    #: The obligation in words, empty when there is none. Sent rather than composed
    #: client-side so one licence cannot be described two ways.
    redistribution_note: str
    installed: bool
    size_on_disk_mb: int
    available: bool = Field(description="False when a gated model has no token.")
    unavailable_reason: str | None = None


class ModelListResponse(BaseModel):
    models: list[ModelInfo]


class DownloadJobResponse(BaseModel):
    job_id: str
    model_id: str
    state: Literal["pending", "downloading", "complete", "failed"]
    downloaded_bytes: int = 0
    total_bytes: int = 0
    message: str = ""


class DeleteResponse(BaseModel):
    id: str
    removed: bool
    freed_mb: int


def _token() -> str | None:
    secret = get_settings().hf_token
    return secret.get_secret_value() if secret else None


def _describe(spec: ModelSpec) -> ModelInfo:
    """Combine a catalogue entry with what is actually on disk."""
    directory = resolve_model_dir(spec.id)
    installed = is_installed(directory)
    has_token = _token() is not None
    available = has_token or not spec.gated

    return ModelInfo(
        id=spec.id,
        repo_id=spec.repo_id,
        kind=spec.kind,
        family=spec.family,
        gated=spec.gated,
        approx_size_mb=spec.approx_size_mb,
        description=spec.description,
        licence=spec.licence,
        licence_url=licence_url(spec),
        requires_access_request=spec.requires_access_request,
        non_commercial=spec.non_commercial,
        starter=spec.starter,
        redistribution=spec.redistribution,
        redistribution_note=REDISTRIBUTION_NOTES[spec.redistribution],
        installed=installed,
        size_on_disk_mb=directory_size_bytes(directory) // _BYTES_PER_MB,
        available=available,
        unavailable_reason=None if available else _unavailable_reason(spec),
    )


def _unavailable_reason(spec: ModelSpec) -> str:
    """Why a gated model cannot be downloaded yet — in the user's next action.

    Two different gates, and saying the wrong one is the most confusing failure this app
    can produce. DINOv3 opens the moment its terms are accepted. SAM 3 additionally needs a
    request a human at Meta approves, so a valid token still returns 403 until then — and
    "set HF_TOKEN" would be advice the user has already followed.
    """
    if spec.requires_access_request:
        return (
            f"Gated model with manual approval. Request access at {licence_url(spec)} "
            f"and accept the {spec.licence}, then add your HuggingFace token below. "
            "Access is granted by a person, so it is not immediate."
        )
    return (
        f"Gated model. Accept the {spec.licence} at {licence_url(spec)}, "
        "then add your HuggingFace token below."
    )


def _job_response(job: DownloadJob) -> DownloadJobResponse:
    return DownloadJobResponse(
        job_id=job.job_id,
        model_id=job.model_id,
        state=job.state,
        downloaded_bytes=job.downloaded_bytes,
        total_bytes=job.total_bytes,
        message=job.message,
    )


def _require_spec(model_id: str) -> ModelSpec:
    """Registry lookup. An unknown id is a 404 — never a filesystem probe."""
    spec = get_model(model_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown model: {model_id}")
    return spec


@router.get("/models", response_model=ModelListResponse, summary="List the model catalogue")
async def list_models() -> ModelListResponse:
    return ModelListResponse(models=[_describe(spec) for spec in all_models()])


@router.post(
    "/models/{model_id}/download",
    response_model=DownloadJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start downloading a model",
)
async def download_model(model_id: str) -> DownloadJobResponse:
    spec = _require_spec(model_id)
    manager = get_download_manager()

    if manager.active_for(spec.id) is not None:
        raise HTTPException(status_code=409, detail=f"Download already running for {spec.id}")

    directory = resolve_model_dir(spec.id)
    if is_installed(directory):
        raise HTTPException(status_code=409, detail=f"{spec.id} is already installed")

    token = _token()
    if spec.gated and token is None:
        raise HTTPException(
            status_code=403,
            detail=(
                f"{spec.id} is gated. Accept the licence at {licence_url(spec)}, "
                "then set HF_TOKEN in .env and restart."
            ),
        )

    logger.info("Starting download for %s", spec.id)
    return _job_response(manager.start(spec, directory, token))


@router.get(
    "/models/jobs/{job_id}",
    response_model=DownloadJobResponse,
    summary="Poll download progress",
)
async def get_job(job_id: str) -> DownloadJobResponse:
    job = get_download_manager().get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job: {job_id}")
    return _job_response(job)


@router.delete("/models/{model_id}", response_model=DeleteResponse, summary="Remove a model")
async def delete_model(model_id: str) -> DeleteResponse:
    spec = _require_spec(model_id)

    if get_download_manager().active_for(spec.id) is not None:
        raise HTTPException(status_code=409, detail=f"Download in progress for {spec.id}")

    try:
        directory = resolve_model_dir(spec.id)
    except PathConfinementError:
        # Unreachable via the registry, but a delete path must never trust that.
        logger.error("Refusing to delete outside the cache root for %s", model_id)
        raise HTTPException(status_code=400, detail="Invalid model path") from None

    if directory == model_cache_root():
        raise HTTPException(status_code=400, detail="Refusing to delete the cache root")

    if not is_installed(directory):
        return DeleteResponse(id=spec.id, removed=False, freed_mb=0)

    freed = directory_size_bytes(directory)
    shutil.rmtree(directory)
    logger.info("Removed %s (%d MB)", spec.id, freed // _BYTES_PER_MB)
    return DeleteResponse(id=spec.id, removed=True, freed_mb=freed // _BYTES_PER_MB)

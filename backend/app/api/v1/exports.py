"""Automatic exports (doc 144): the settings, the last run, and a run."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.env_file import write_env_value
from app.datasets.exchange.auto import (
    AutoReport,
    is_running,
    last_report,
    run_exports,
    start_in_background,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class ExportSettings(BaseModel):
    on_close: bool
    every_minutes: int = Field(ge=0, le=1440, description="0: off.")
    #: Doc 145: trained models exported here when their training finishes; None: off.
    #: A PUT without the field leaves it as it is.
    model_folder: str | None = None


class ExportStatus(BaseModel):
    running: bool
    last: AutoReport | None


class RunRequest(BaseModel):
    #: "close", "interval" or "manual".
    reason: str = Field(default="manual", pattern="^(close|interval|manual)$")
    #: True: run now and answer with the report (closing). False: start in the background.
    wait: bool = True
    deadline_seconds: float | None = Field(default=None, gt=0, le=600)


class RunResponse(BaseModel):
    #: "done", "started", "busy" (a run is going) or "off" (closing with the setting off).
    outcome: str
    report: AutoReport | None = None


@router.get(
    "/exports/settings", response_model=ExportSettings, summary="When datasets export by themselves"
)
def get_export_settings() -> ExportSettings:
    settings = get_settings()
    return ExportSettings(
        on_close=settings.export_on_close,
        every_minutes=settings.export_every_minutes,
        model_folder=settings.model_export_folder,
    )


@router.put(
    "/exports/settings",
    response_model=ExportSettings,
    summary="Choose when datasets export by themselves (.env)",
)
def put_export_settings(request: ExportSettings) -> ExportSettings:
    folder = (request.model_folder or "").strip()
    # Checked before anything is written: a refused request changes nothing.
    if folder and not Path(folder).expanduser().is_absolute():
        raise HTTPException(status_code=422, detail=f"Choose a full folder path, not {folder!r}.")
    write_env_value("DINO_EXPORT_ON_CLOSE", "true" if request.on_close else "false")
    write_env_value("DINO_EXPORT_EVERY_MINUTES", str(request.every_minutes))
    if "model_folder" in request.model_fields_set:
        write_env_value("DINO_MODEL_EXPORT_FOLDER", folder)
    get_settings.cache_clear()
    return get_export_settings()


@router.get(
    "/exports/status",
    response_model=ExportStatus,
    summary="Whether a run is going, and the last run",
)
def export_status() -> ExportStatus:
    return ExportStatus(running=is_running(), last=last_report())


@router.post(
    "/exports/run", response_model=RunResponse, summary="Export every changed dataset to its target"
)
def run(request: RunRequest) -> RunResponse:
    if request.reason == "close" and not get_settings().export_on_close:
        return RunResponse(outcome="off")
    if not request.wait:
        return RunResponse(outcome="started" if start_in_background(request.reason) else "busy")
    report = run_exports(request.reason, request.deadline_seconds)
    return RunResponse(outcome="done", report=report) if report else RunResponse(outcome="busy")

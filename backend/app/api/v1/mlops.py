"""MLflow settings and status (doc 123). Secrets go into `.env` and never come back out."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.env_file import write_env_value
from app.mlops.backfill import as_dict, get_backfill, start_backfill
from app.mlops.mlflow_client import MlflowClient, MlflowError

logger = logging.getLogger(__name__)
router = APIRouter()


class MlflowStatus(BaseModel):
    configured: bool
    uri: str | None
    experiment: str
    register_models: bool
    #: Which credentials are set — never their values.
    auth: str  # "none" | "basic" | "token"
    username: str | None


class MlflowSettingsRequest(BaseModel):
    uri: str = Field(min_length=1, max_length=500)
    experiment: str = Field(default="DinoTraining", min_length=1, max_length=200)
    register_models: bool = True
    #: Left out: keep what is stored. An empty string: remove it.
    username: str | None = None
    password: str | None = None
    token: str | None = None


class TestResult(BaseModel):
    ok: bool
    message: str
    experiment_id: str | None = None


def _status() -> MlflowStatus:
    settings = get_settings()
    auth = "token" if settings.mlflow_token else "basic" if settings.mlflow_password else "none"
    return MlflowStatus(
        configured=bool(settings.mlflow_uri),
        uri=settings.mlflow_uri,
        experiment=settings.mlflow_experiment,
        register_models=settings.mlflow_register,
        auth=auth,
        username=settings.mlflow_username,
    )


@router.get("/mlops/status", response_model=MlflowStatus, summary="MLflow set up or not")
def get_status() -> MlflowStatus:
    return _status()


@router.put("/mlops/settings", response_model=MlflowStatus, summary="Set up MLflow (.env)")
def put_settings(request: MlflowSettingsRequest) -> MlflowStatus:
    uri = request.uri.strip()
    if not uri.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=422, detail="The tracking URI must start with http:// or https://."
        )
    write_env_value("MLFLOW_TRACKING_URI", uri)
    write_env_value("DINO_MLFLOW_EXPERIMENT", request.experiment.strip())
    write_env_value("DINO_MLFLOW_REGISTER", "true" if request.register_models else "false")
    for key, value in (
        ("MLFLOW_TRACKING_USERNAME", request.username),
        ("MLFLOW_TRACKING_PASSWORD", request.password),
        ("MLFLOW_TRACKING_TOKEN", request.token),
    ):
        if value is not None:
            write_env_value(key, value.strip())
    get_settings.cache_clear()
    logger.info("MLflow settings updated by the user")  # never the values
    return _status()


@router.delete("/mlops/settings", response_model=MlflowStatus, summary="Turn MLflow off")
def delete_settings() -> MlflowStatus:
    for key in ("MLFLOW_TRACKING_URI", "MLFLOW_TRACKING_PASSWORD", "MLFLOW_TRACKING_TOKEN"):
        write_env_value(key, "")
    get_settings.cache_clear()
    return _status()


@router.post("/mlops/test", response_model=TestResult, summary="Reach MLflow and its experiment")
def post_test() -> TestResult:
    settings = get_settings()
    try:
        experiment = MlflowClient(settings).experiment_id(settings.mlflow_experiment)
    except MlflowError as error:
        return TestResult(ok=False, message=str(error))
    return TestResult(
        ok=True,
        message=f"Connected. Experiment '{settings.mlflow_experiment}' has id {experiment}.",
        experiment_id=experiment,
    )


@router.post("/mlops/backfill", summary="Send the models trained before to MLflow (a job)")
def post_backfill() -> dict[str, Any]:
    if not get_settings().mlflow_uri:
        raise HTTPException(status_code=409, detail="MLflow is not set up: no tracking URI.")
    return as_dict(start_backfill())


@router.get("/mlops/backfill/{job_id}", summary="A backfill's progress")
def get_backfill_job(job_id: str) -> dict[str, Any]:
    job = get_backfill(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"No such backfill: {job_id}")
    return as_dict(job)


__all__ = ["router"]

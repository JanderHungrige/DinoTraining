"""Data preparation: targets and the dataset audit (doc 81)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.datasets.store import DatasetStore
from app.prep.audit import DatasetAudit, last_audit, run_audit
from app.prep.jobs import PrepJob, get_prep_runner
from app.prep.profiles import list_profiles

router = APIRouter()


class TargetInfo(BaseModel):
    id: str
    label: str
    task: str
    annotation_kind: str
    input_size: int
    min_visible_px: int


class AuditRequest(BaseModel):
    #: A target from GET /prep/targets. Without one, size rules that need a model are skipped.
    target: str | None = None


class AuditJob(BaseModel):
    job_id: str
    state: str
    done: int
    total: int
    message: str
    audit: DatasetAudit | None = None


def _describe(job: PrepJob) -> AuditJob:
    result = job.result if isinstance(job.result, DatasetAudit) else None
    return AuditJob(
        job_id=job.job_id,
        state=job.state,
        done=job.done,
        total=job.total,
        message=job.message,
        audit=result,
    )


@router.get(
    "/prep/targets", response_model=list[TargetInfo], summary="Models data can be prepared for"
)
async def list_targets() -> list[TargetInfo]:
    return [
        TargetInfo(
            id=p.id,
            label=p.label,
            task=p.task,
            annotation_kind=p.annotation_kind,
            input_size=p.input_size,
            min_visible_px=p.min_visible_px,
        )
        for p in list_profiles()
    ]


@router.post(
    "/datasets/{dataset_id}/audit",
    response_model=AuditJob,
    status_code=202,
    summary="Audit a dataset for a target model (a job)",
)
async def start_audit(dataset_id: str, request: AuditRequest) -> AuditJob:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")
    known = {p.id for p in list_profiles()}
    if request.target is not None and request.target not in known:
        raise HTTPException(status_code=422, detail=f"Unknown target: {request.target}")
    job = get_prep_runner().submit(
        "audit", lambda _job, progress: run_audit(dataset_id, request.target, progress)
    )
    return _describe(job)


@router.get(
    "/prep/audits/{job_id}", response_model=AuditJob, summary="An audit's progress and report"
)
async def get_audit_job(job_id: str) -> AuditJob:
    job = get_prep_runner().get(job_id)
    if job is None or job.kind != "audit":
        raise HTTPException(status_code=404, detail=f"No such audit: {job_id}")
    return _describe(job)


@router.get(
    "/datasets/{dataset_id}/audit",
    response_model=DatasetAudit,
    summary="The last audit of a dataset",
)
async def get_last_audit(dataset_id: str) -> DatasetAudit:
    audit = last_audit(dataset_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="This dataset has not been audited yet.")
    return audit


__all__ = ["router"]

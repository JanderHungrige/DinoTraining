"""Example datasets fetched in one click (doc 138): what there is, and import one."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.api.v1.dataset_import import ImportJobView, view_job
from app.datasets.examples.catalogue import EXAMPLES, ExampleView, Variant, view
from app.datasets.examples.fetch import downloaded
from app.datasets.intake.jobs import get_import_jobs

router = APIRouter()


class ExampleList(BaseModel):
    examples: list[ExampleView]


class ExampleImportRequest(BaseModel):
    variant: Variant


@router.get(
    "/datasets/examples",
    response_model=ExampleList,
    summary="Example datasets the app can download and import in one click",
)
async def examples() -> ExampleList:
    jobs = get_import_jobs()
    listed = []
    for example in EXAMPLES.values():
        running = jobs.running_example(example.example_id)
        listed.append(view(example, downloaded(example), running.job_id if running else None))
    return ExampleList(examples=listed)


@router.post(
    "/datasets/examples/{example_id}/import",
    response_model=ImportJobView,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Download an example (unless already there) and import it (runs in the background)",
)
async def import_example(example_id: str, request: ExampleImportRequest) -> ImportJobView:
    example = EXAMPLES.get(example_id)
    if example is None:
        raise HTTPException(status_code=404, detail=f"No example dataset {example_id}")
    return view_job(get_import_jobs().submit_example(example, request.variant))

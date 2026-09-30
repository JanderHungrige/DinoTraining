"""Export bundles (doc 121): a zip that runs a trained model outside the app."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field

from app.mlops.export import export_payload, export_to, model_folder

router = APIRouter()

Kind = Literal["heads", "finetuned"]


class ExportRequest(BaseModel):
    kind: Kind
    instance_id: str = Field(min_length=1)
    #: A folder to write `<name>.zip` into (the desktop picker). Absent: the zip is returned.
    destination: str | None = None


@router.post(
    "/exports",
    summary="Export a trained model as a zip: card, weights, runtime, example, README",
    response_model=None,
)
def post_export(request: ExportRequest) -> Response | dict[str, str]:
    try:
        if request.destination:
            target = export_to(request.kind, request.instance_id, Path(request.destination))
            return {"path": str(target), "file": target.name}
        name, data = export_payload(request.kind, request.instance_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get(
    "/exports/{kind}/{instance_id}/location",
    summary="The folder that holds a trained model, for 'Show where it is'",
)
def get_location(kind: Kind, instance_id: str) -> dict[str, str]:
    try:
        return {"folder": str(model_folder(kind, instance_id))}
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


__all__ = ["router"]

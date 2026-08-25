"""Trained, imported and default heads — the picker contract for every tab.

Waves 3 and 4 read this list. It returns what a head *does* and what it was trained on,
never a bare filename, which is the whole reason the feature exists.
"""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.datasets.db import transaction
from app.datasets.images import median_width
from app.ml.heads.instances import HeadInstance, HeadInstanceKind
from app.ml.heads.registry import RenderHint, get_head_type
from app.ml.heads.store import HeadInstanceNotFoundError, HeadInstanceStore

logger = logging.getLogger(__name__)
router = APIRouter()


#: What an instance whose head type is no longer in the registry reports. A community
#: import can outlive a type; claiming it draws boxes would put it in an annotator picker
#: that then fails at run time, so it reports the one hint nothing dispatches on.
UNKNOWN_RENDER_HINT: RenderHint = "labels"


def _render_hint(head_type_id: str) -> RenderHint:
    spec = get_head_type(head_type_id)
    return spec.render_hint if spec is not None else UNKNOWN_RENDER_HINT


class HeadInstanceInfo(BaseModel):
    id: str
    name: str
    summary: str = Field(description="One-line description every picker renders.")
    kind: HeadInstanceKind
    head_type_id: str
    task: str
    #: What this head's output can be drawn as, from the head-type registry. Exposed so a
    #: picker asks "can this annotate boxes?" of the authoritative field instead of
    #: inferring it from `task` — the same reason `components/overlays/` dispatches on the
    #: render hint and a `task ===` comparison there is a defect.
    render_hint: RenderHint
    backbone_id: str
    backbone_family: str
    embed_dim: int
    num_classes: int
    class_names: list[str]
    dataset_ids: list[str]
    metrics: dict[str, float]
    primary_metric: str | None
    primary_metric_value: float | None
    epochs_trained: int
    best_epoch: int | None
    source_repo: str | None
    created_at: str
    #: Median width of the images this head trained on, or null when the datasets are
    #: gone. Powers doc 62's tiling hint — "trained on 616 px, running on 2464 px" — and
    #: nothing acts on it. Null is expected: a dataset can be deleted after training, and
    #: a listing must not break because one was.
    trained_width: int | None = None


class HeadInstanceListResponse(BaseModel):
    heads: list[HeadInstanceInfo]


class DeleteResponse(BaseModel):
    id: str
    removed: bool


def describe_instance(
    instance: HeadInstance, trained_width: int | None = None
) -> HeadInstanceInfo:
    """Instance -> API shape. Public because doc 15's catalogue router returns the
    same model — a second copy is how two endpoints start describing one head
    differently."""
    return HeadInstanceInfo(
        id=instance.id,
        name=instance.name,
        summary=instance.summary,
        kind=instance.kind,
        head_type_id=instance.head_type_id,
        task=instance.task,
        render_hint=_render_hint(instance.head_type_id),
        backbone_id=instance.backbone_id,
        backbone_family=instance.backbone_family,
        embed_dim=instance.embed_dim,
        num_classes=instance.num_classes,
        class_names=list(instance.class_names),
        dataset_ids=list(instance.dataset_ids),
        metrics=instance.metrics,
        primary_metric=instance.primary_metric,
        primary_metric_value=instance.primary_metric_value,
        epochs_trained=instance.epochs_trained,
        best_epoch=instance.best_epoch,
        source_repo=instance.source_repo,
        created_at=instance.created_at,
        trained_width=trained_width,
    )


@router.get("/heads", response_model=HeadInstanceListResponse, summary="List usable heads")
async def list_heads(
    task: str | None = Query(default=None, description="Filter by task — powers comparison."),
    backbone: str | None = Query(default=None, description="Hide heads that cannot run."),
) -> HeadInstanceListResponse:
    instances = HeadInstanceStore().list_all(task=task, backbone_id=backbone)
    return HeadInstanceListResponse(
        heads=[describe_instance(instance, _trained_width(instance)) for instance in instances]
    )


def _trained_width(instance: HeadInstance) -> int | None:
    """The median width of what this head trained on, for doc 62's tiling hint.

    Failure is swallowed on purpose. This decorates a listing that must render whether or
    not the datasets still exist — a hint nobody can compute is a missing hint, never a
    500 on the picker that every tab depends on.
    """
    if not instance.dataset_ids:
        return None
    try:
        with transaction() as connection:
            return median_width(connection, list(instance.dataset_ids))
    except sqlite3.Error:  # pragma: no cover - a listing must not fail for a hint
        logger.warning("Could not read the training width for head %s", instance.id)
        return None


@router.get(
    "/heads/{instance_id}", response_model=HeadInstanceInfo, summary="One head's full record"
)
async def get_head(instance_id: str) -> HeadInstanceInfo:
    try:
        instance = HeadInstanceStore().get(instance_id)
        return describe_instance(instance, _trained_width(instance))
    except HeadInstanceNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown head: {instance_id}") from None


@router.delete("/heads/{instance_id}", response_model=DeleteResponse, summary="Delete a head")
async def delete_head(instance_id: str) -> DeleteResponse:
    # Idempotent: deleting an already-absent head is the state the caller wanted, not an
    # error worth surfacing as a failure in the UI.
    removed = HeadInstanceStore().delete(instance_id)
    return DeleteResponse(id=instance_id, removed=removed)

"""Trained, imported and default heads — the picker contract for every tab.

Waves 3 and 4 read this list. It returns what a head *does* and what it was trained on,
never a bare filename, which is the whole reason the feature exists.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.ml.heads.instances import HeadInstance, HeadInstanceKind
from app.ml.heads.store import HeadInstanceNotFoundError, HeadInstanceStore

logger = logging.getLogger(__name__)
router = APIRouter()


class HeadInstanceInfo(BaseModel):
    id: str
    name: str
    summary: str = Field(description="One-line description every picker renders.")
    kind: HeadInstanceKind
    head_type_id: str
    task: str
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


class HeadInstanceListResponse(BaseModel):
    heads: list[HeadInstanceInfo]


class DeleteResponse(BaseModel):
    id: str
    removed: bool


def describe_instance(instance: HeadInstance) -> HeadInstanceInfo:
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
    )


@router.get("/heads", response_model=HeadInstanceListResponse, summary="List usable heads")
async def list_heads(
    task: str | None = Query(default=None, description="Filter by task — powers comparison."),
    backbone: str | None = Query(default=None, description="Hide heads that cannot run."),
) -> HeadInstanceListResponse:
    instances = HeadInstanceStore().list_all(task=task, backbone_id=backbone)
    return HeadInstanceListResponse(heads=[describe_instance(instance) for instance in instances])


@router.get(
    "/heads/{instance_id}", response_model=HeadInstanceInfo, summary="One head's full record"
)
async def get_head(instance_id: str) -> HeadInstanceInfo:
    try:
        return describe_instance(HeadInstanceStore().get(instance_id))
    except HeadInstanceNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown head: {instance_id}") from None


@router.delete("/heads/{instance_id}", response_model=DeleteResponse, summary="Delete a head")
async def delete_head(instance_id: str) -> DeleteResponse:
    # Idempotent: deleting an already-absent head is the state the caller wanted, not an
    # error worth surfacing as a failure in the UI.
    removed = HeadInstanceStore().delete(instance_id)
    return DeleteResponse(id=instance_id, removed=removed)

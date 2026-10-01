"""Cloud storage connections (doc 147): add, change, remove, test. Secrets go in, never out."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.cloud.cache import bound_bytes, clear, evict, per_dataset, used_bytes
from app.cloud.connections import (
    Connection,
    ConnectionRequest,
    create_connection,
    delete_connection,
    get_connection,
    list_connections,
    update_connection,
)
from app.cloud.errors import CloudError
from app.cloud.links import forget_storages
from app.cloud.storage import open_storage, probe_storage
from app.core.config import get_settings
from app.core.env_file import write_env_value

logger = logging.getLogger(__name__)
router = APIRouter()


class TestRequest(BaseModel):
    bucket: str = Field(min_length=1, description="The bucket (S3, GCS) or container (Azure).")
    prefix: str = ""


class TestResult(BaseModel):
    ok: bool
    message: str


def _found(connection_id: str) -> Connection:
    try:
        return get_connection(connection_id)
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.get(
    "/cloud/connections",
    response_model=list[Connection],
    summary="Cloud storage accounts (no secrets)",
)
def connections() -> list[Connection]:
    return list_connections()


@router.post(
    "/cloud/connections",
    response_model=Connection,
    status_code=201,
    summary="Add a cloud storage account",
)
def add(request: ConnectionRequest) -> Connection:
    try:
        return create_connection(request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.put(
    "/cloud/connections/{connection_id}",
    response_model=Connection,
    summary="Change one; empty secrets are kept",
)
def change(connection_id: str, request: ConnectionRequest) -> Connection:
    _found(connection_id)
    try:
        updated = update_connection(connection_id, request)
        forget_storages(connection_id)  # doc 149: linked datasets use the new settings at once
        return updated
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/cloud/connections/{connection_id}", summary="Remove one and its secrets")
def remove(connection_id: str) -> dict[str, bool]:
    _found(connection_id)
    delete_connection(connection_id)
    forget_storages(connection_id)
    return {"deleted": True}


@router.post(
    "/cloud/connections/{connection_id}/test",
    response_model=TestResult,
    summary="List one key of a bucket",
)
def test(connection_id: str, request: TestRequest) -> TestResult:
    connection = _found(connection_id)
    try:
        storage = open_storage(connection, request.bucket.strip(), request.prefix)
        return TestResult(ok=True, message=probe_storage(storage))
    except CloudError as error:
        logger.info("Cloud test of %s (%s) failed: %s", connection.name, request.bucket, error)
        return TestResult(ok=False, message=str(error))
    except Exception as error:  # noqa: BLE001 - a misconfigured store fails while being built
        logger.info("Cloud test of %s could not start: %s", connection.name, error)
        return TestResult(ok=False, message=f"The connection's settings were refused: {error}")


class LinkedUse(BaseModel):
    dataset_id: str
    uri: str
    pictures: int
    cached: int


class CacheState(BaseModel):
    bound_gb: float
    used_bytes: int
    datasets: list[LinkedUse]


class CacheBound(BaseModel):
    bound_gb: float = Field(gt=0, le=10_000)


def _cache_state() -> CacheState:
    return CacheState(
        bound_gb=get_settings().cloud_cache_gb,
        used_bytes=used_bytes(),
        datasets=[LinkedUse(**vars(entry)) for entry in per_dataset()],
    )


@router.get(
    "/cloud/cache",
    response_model=CacheState,
    summary="The linked pictures' cache: its bound and use",
)
def cache() -> CacheState:
    return _cache_state()


@router.put("/cloud/cache", response_model=CacheState, summary="Change the cache's bound (.env)")
def set_cache(request: CacheBound) -> CacheState:
    write_env_value("DINO_CLOUD_CACHE_GB", f"{request.bound_gb:g}")
    get_settings.cache_clear()
    if used_bytes() > bound_bytes():
        evict(int(bound_bytes() * 0.9))
    return _cache_state()


@router.post("/cloud/cache/clear", response_model=CacheState, summary="Remove every cached picture")
def clear_cache() -> CacheState:
    clear()
    return _cache_state()

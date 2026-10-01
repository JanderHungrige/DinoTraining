"""Cloud storage connections (doc 147): add, change, remove, test. Secrets go in, never out."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

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
from app.cloud.storage import open_storage, probe_storage

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
        return update_connection(connection_id, request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@router.delete("/cloud/connections/{connection_id}", summary="Remove one and its secrets")
def remove(connection_id: str) -> dict[str, bool]:
    _found(connection_id)
    delete_connection(connection_id)
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

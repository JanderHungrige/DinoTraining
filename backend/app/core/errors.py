"""Shaped error responses and global exception handlers.

Two rules drive this module:

* Errors are logged with context *before* being re-raised or converted — a swallowed
  exception is a bug report you will never receive.
* The client gets a stable, machine-readable shape and never a traceback. Internal
  detail stays in the log where the developer can reach it.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    409: "conflict",
    413: "payload_too_large",
    422: "validation_error",
    500: "internal_error",
    503: "service_unavailable",
}


def error_body(code: str, message: str, details: Any | None = None) -> dict[str, Any]:
    """Build the canonical error envelope: ``{"error": {...}}``."""
    error: dict[str, Any] = {"code": code, "message": message}
    if details is not None:
        error["details"] = details
    return {"error": error}


def _code_for_status(status_code: int) -> str:
    return _STATUS_CODES.get(status_code, "error")


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Convert HTTPException into the canonical envelope, preserving status."""
    assert isinstance(exc, StarletteHTTPException)
    logger.info(
        "HTTP %s on %s %s — %s", exc.status_code, request.method, request.url.path, exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_body(_code_for_status(exc.status_code), str(exc.detail)),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Surface request-validation failures without echoing raw internals."""
    assert isinstance(exc, RequestValidationError)
    logger.info("Validation failure on %s %s — %s", request.method, request.url.path, exc.errors())
    return JSONResponse(
        status_code=422,
        content=error_body(
            "validation_error",
            "Request validation failed.",
            details=[
                {"field": ".".join(str(p) for p in err.get("loc", ())), "issue": err.get("msg", "")}
                for err in exc.errors()
            ],
        ),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Last resort. Log the full traceback, return an opaque 500."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content=error_body(
            "internal_error",
            "An internal error occurred. Check the backend log for details.",
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every handler above to the application."""
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

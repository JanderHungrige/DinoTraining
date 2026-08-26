"""How an MCP tool reaches the app: through its own HTTP routes, in-process.

**Not by importing the store.** That was the tempting shortcut and it is the wrong one:
this project has a single shared connection module precisely so one process owns the
SQLite file, and a tool layer that imported `DatasetStore` would be a second owner with a
second connection and its own idea of when a transaction ends.

**Not over a real socket either.** `ASGITransport` dispatches straight into the same app
object, so a tool call goes through the full route stack — validation, the error handlers,
the `ValueError → 422` backstops — without a port, a DNS lookup or an assumption about
what the sidecar is bound to. It is what `tests/datasets_api_testkit.py` already does, and
it means a tool cannot behave differently from the endpoint it wraps.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import FastAPI

logger = logging.getLogger(__name__)

#: Long enough for a model download to *start* and a fine-tune to be accepted. No tool
#: waits for one to finish — those return a job id and the assistant polls.
TIMEOUT = 120.0

_app: FastAPI | None = None


def bind(app: FastAPI) -> None:
    """Give the tool layer the app it should call. Set once, by `mount_mcp`."""
    global _app
    _app = app


class ApiError(RuntimeError):
    """A non-2xx from the app, carrying the message the API wrote for a person.

    Raised rather than returned: an MCP client renders a raised error as a tool failure the
    model can read and act on, while a dict with an `error` key is just as likely to be
    summarised as success.
    """

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"{status}: {message}")
        self.status = status
        self.message = message


async def call(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> Any:
    """One request against the app's own API. Returns parsed JSON, raises `ApiError`.

    `path` is relative to `/api/v1`, so a tool names the route the guide names.
    """
    if _app is None:  # pragma: no cover - mount_mcp always binds first
        raise RuntimeError("The MCP tool layer was used before it was bound to an app.")

    transport = httpx.ASGITransport(app=_app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://mcp.local", timeout=TIMEOUT
    ) as client:
        response = await client.request(
            method, f"/api/v1{path}", json=json, params=params
        )

    if response.status_code >= 400:
        raise ApiError(response.status_code, _message(response))
    if not response.content:
        return None
    if response.headers.get("content-type", "").startswith("text/"):
        return response.text
    return response.json()


def _message(response: httpx.Response) -> str:
    """The API's own explanation, which is written for a reader and names the fix.

    Falls back to the raw body: a 500 from somewhere without the error envelope is still
    more useful quoted than replaced with "request failed".
    """
    try:
        body = response.json()
    except ValueError:
        return response.text[:400] or response.reason_phrase
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message
        detail = body.get("detail")
        if isinstance(detail, str):
            return detail
    return str(body)[:400]


__all__ = ["ApiError", "TIMEOUT", "bind", "call"]

"""Building the MCP server and mounting it on the sidecar (doc 64).

**Mounted on the app that already runs, not a second process.** The sidecar is up whenever
the desktop app is, on a known port, so there is nothing to install and nothing to launch.
A standalone stdio server would have re-solved the packaging problem Wave 8 already solved.

Five things a spike found, each of which would otherwise have been an afternoon:

* `mcp` 2.x renamed `FastMCP` to `MCPServer`; every v1 example fails to import.
* the mount path and the transport security are **keyword arguments to
  `streamable_http_app()`**, not settings on the constructor;
* **DNS-rebinding protection is on by default** and rejects any `Host` it does not know,
  with a 421 that does not mention an allowlist;
* the session manager runs inside a lifespan, and FastAPI does **not** run a mounted
  sub-app's lifespan — so it has to be composed into the parent's, or every tool call
  fails at request time with "Task group is not initialized" long after startup looked
  fine;
* `stateless_http=True` removes the session handshake, which is right for one local user
  and makes every request self-contained.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

from app.mcp import client, tools

logger = logging.getLogger(__name__)

#: Where the tool endpoint lives, and what the setup command points at.
MCP_PATH = "/mcp"

INSTRUCTIONS = """DinoTraining annotates images, trains models on them, and generates more
annotated data with what it trained.

Start with `get_guide` for anything needing several steps — it documents the order, which
no tool schema can. Long work returns a job id: poll `get_job` and report the metrics as
they move. Every path is absolute and on this machine; there is no upload."""


def _security(host: str, port: int) -> TransportSecuritySettings:
    """The loopback names this server answers to, and nothing else.

    Protection against DNS rebinding, which is a real attack on a local HTTP server: a page
    the user visits resolves a name it controls to 127.0.0.1 and drives the tools. The
    allowlist is what stops it, so it is built from the configured bind address rather than
    widened until a request works.
    """
    hosts = [f"{host}:{port}", f"localhost:{port}", f"127.0.0.1:{port}"]
    return TransportSecuritySettings(
        allowed_hosts=sorted(set(hosts)),
        allowed_origins=sorted({f"http://{entry}" for entry in hosts}),
    )


def build() -> MCPServer:
    """The server with every tool attached."""
    mcp = MCPServer("dinotraining", instructions=INSTRUCTIONS)
    tools.register(mcp)
    return mcp


def mount_mcp(app: FastAPI, host: str, port: int) -> None:
    """Attach the MCP endpoint to a FastAPI app and bind the tool layer to it.

    **The sub-app is rooted at `/` and mounted at `MCP_PATH`**, not the other way round.
    `streamable_http_app` routes its own path, so leaving that as `/mcp` and mounting at
    `/mcp` serves the endpoint from `/mcp/mcp` — a 404 that reads exactly like the server
    not being there. Mounting at `""` fixes the URL and creates a worse problem: a mount
    with an empty prefix matches *everything*, so it becomes a catch-all at the end of the
    route table and silently kills any route registered after it. Rooting the sub-app at
    `/` and mounting at `/mcp` is the only arrangement that is both correct and contained.
    """
    mcp = build()
    sub = mcp.streamable_http_app(
        streamable_http_path="/",
        stateless_http=True,
        transport_security=_security(host, port),
    )

    client.bind(app)
    app.mount(MCP_PATH, sub)
    _compose_lifespan(app, sub)
    logger.info("MCP tools at http://%s:%d%s", host, port, MCP_PATH)


def _compose_lifespan(app: FastAPI, sub: Any) -> None:
    """Run the sub-app's lifespan alongside the parent's.

    Composed rather than replaced, so anything the app already does on startup still runs.
    """
    parent = app.router.lifespan_context
    child = sub.router.lifespan_context

    @asynccontextmanager
    async def combined(scope: Any) -> AsyncIterator[None]:
        async with child(scope), parent(scope):
            yield

    app.router.lifespan_context = combined


__all__ = ["MCP_PATH", "build", "mount_mcp"]

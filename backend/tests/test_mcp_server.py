"""The MCP tool server (doc 64).

Two kinds of risk, needing different tests.

**Protocol.** The mount is five non-obvious settings deep and four of the five fail at
*request* time rather than at startup — a 404 that reads like the server is absent, a 421
that never mentions an allowlist, a "task group is not initialized" long after startup
looked fine. So the tests drive the real JSON-RPC endpoint rather than calling the tool
functions directly.

**Contract.** The tools *are* the documentation an assistant reads: name, description and
parameter types are all it sees before choosing. So what matters is that they exist, that
the silent traps are named in the descriptions, and that a failure reaches the model as a
failure rather than as a plausible-looking success.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app
from app.mcp import client
from app.mcp.server import MCP_PATH, build


@asynccontextmanager
async def running_app(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[FastAPI]:
    """The real app on a throwaway data root, with its lifespan actually running.

    **A context manager rather than a fixture, and that is not a style preference.** The MCP
    session manager holds an anyio task group open across the lifespan, and a task group has
    to be exited by the task that entered it. pytest-asyncio runs fixture setup and teardown
    as two different tasks, so yielding from a fixture gives every test a pass and every
    teardown a "RuntimeError: Attempted to exit cancel scope in a different task". Entered
    inside the test body it is one task, which is also what uvicorn does.

    The lifespan itself is not optional: `httpx.ASGITransport` does not run one, and without
    it the task group never starts and every tool call fails at request time.
    """
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_connection()
    try:
        built = create_app()
        async with built.router.lifespan_context(built):
            yield built
    finally:
        reset_connection()
        get_settings.cache_clear()


async def rpc(app: FastAPI, method: str, params: dict[str, Any] | None = None) -> Any:
    """One JSON-RPC call against the mounted endpoint, as a real client makes it."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://127.0.0.1:8756", follow_redirects=True
    ) as http:
        response = await http.post(
            MCP_PATH,
            json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
            headers={
                "Accept": "application/json, text/event-stream",
                "Content-Type": "application/json",
            },
        )
    assert response.status_code == 200, response.text
    # Stateless streamable HTTP answers as a single SSE frame.
    return json.loads(response.text.split("data: ", 1)[1])


async def tool_list(app: FastAPI) -> list[dict[str, Any]]:
    body = await rpc(app, "tools/list")
    assert "result" in body, body
    return list(body["result"]["tools"])


async def descriptions(app: FastAPI) -> dict[str, str]:
    return {tool["name"]: tool["description"] for tool in await tool_list(app)}


class TestTheMount:
    async def test_the_endpoint_answers_json_rpc(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Four of the five mount settings fail at request time, not at startup. This is
        the test that would have caught every one of them."""
        async with running_app(tmp_path, monkeypatch) as app:
            assert await tool_list(app)

    async def test_a_wrong_host_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DNS-rebinding protection, and it is not theoretical: a page the user visits can
        resolve a name it controls to 127.0.0.1 and drive these tools. The allowlist built
        from the configured bind address is what stops it."""
        async with running_app(tmp_path, monkeypatch) as app:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport, base_url="http://evil.example", follow_redirects=True
            ) as http:
                response = await http.post(
                    MCP_PATH,
                    json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
                    headers={"Accept": "application/json, text/event-stream"},
                )

            assert response.status_code == 421


class TestTheToolContract:
    async def test_it_offers_task_shaped_tools_not_one_per_endpoint(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The API has 61 operations. One tool each would flood the context and leave the
        model orchestrating anyway — the problem the guide exists to solve."""
        async with running_app(tmp_path, monkeypatch) as app:
            names = {tool["name"] for tool in await tool_list(app)}

        assert names == {
            "list_models",
            "list_datasets",
            "list_heads",
            "get_guide",
            "install_model",
            "get_job",
            "train_head",
            "finetune_model",
            "import_coco_dataset",
            "create_dataset",
            "list_folder_images",
            "export_dataset",
            "propose_annotations",
            "save_annotations",
            "run_inference",
        }

    async def test_every_tool_describes_itself(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The description *is* the prompt — all the model sees before choosing.
        async with running_app(tmp_path, monkeypatch) as app:
            for tool in await tool_list(app):
                assert tool.get("description"), f"{tool['name']} has no description"

    async def test_the_silent_traps_are_named_in_the_descriptions(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Both of this app's silent failures are ones an assistant would otherwise walk
        into, and a tool schema is the only place it reads before acting."""
        async with running_app(tmp_path, monkeypatch) as app:
            described = await descriptions(app)

        # Sending `text` instead of `prompt` drops the class with no error at all (doc 31).
        assert "prompt" in described["save_annotations"]
        # A tile-trained head finds nothing on a full frame — and the call succeeds (doc 62).
        assert "tile" in described["run_inference"].lower()

    async def test_a_job_starting_tool_points_at_get_job(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Blocking a tool call for four minutes hits a client timeout and loses the run.
        async with running_app(tmp_path, monkeypatch) as app:
            described = await descriptions(app)

        for name in ("install_model", "train_head", "finetune_model"):
            assert "get_job" in described[name], f"{name} does not point at get_job"

    async def test_parameters_are_typed_rather_than_free_text(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The point of tools over a prose guide: the schema constrains the call."""
        async with running_app(tmp_path, monkeypatch) as app:
            by_name = {tool["name"]: tool for tool in await tool_list(app)}

        schema = by_name["get_job"]["inputSchema"]
        assert set(schema["required"]) == {"job_id", "kind"}
        # `kind` is an enum, so the model cannot invent a fourth job type.
        assert "enum" in json.dumps(schema)


class TestToolsAgainstTheRealApi:
    async def test_a_tool_reaches_the_app_and_returns_its_data(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with running_app(tmp_path, monkeypatch) as app:
            body = await rpc(app, "tools/call", {"name": "list_datasets", "arguments": {}})

        assert body["result"].get("isError") is not True, body

    async def test_a_created_dataset_is_visible_to_the_next_tool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two tools end to end, which is what proves the in-process client shares the
        app's own database rather than opening a second connection to it."""
        async with running_app(tmp_path, monkeypatch) as app:
            await rpc(
                app,
                "tools/call",
                {"name": "create_dataset", "arguments": {"name": "From MCP"}},
            )
            listed = await rpc(
                app, "tools/call", {"name": "list_datasets", "arguments": {}}
            )

        assert "From MCP" in str(listed["result"])

    async def test_a_failure_reaches_the_model_as_a_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A dict with an `error` key is as likely to be summarised as success. Raising
        makes the client mark the call failed."""
        async with running_app(tmp_path, monkeypatch) as app:
            body = await rpc(
                app,
                "tools/call",
                {"name": "get_job", "arguments": {"job_id": "nope", "kind": "training"}},
            )

        assert body["result"]["isError"] is True

    async def test_the_guide_is_reachable_as_a_tool(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The tools cover the calls; the guide covers the order. An assistant needs both.
        async with running_app(tmp_path, monkeypatch) as app:
            body = await rpc(app, "tools/call", {"name": "get_guide", "arguments": {}})

        assert "workflow" in str(body["result"]).lower()


class TestTheClientLayer:
    def test_every_job_kind_maps_to_a_route(self) -> None:
        from app.mcp.tools import _JOB_PATHS

        assert set(_JOB_PATHS) == {"download", "training", "finetune"}
        assert all("{job_id}" in path for path in _JOB_PATHS.values())

    def test_the_server_carries_instructions(self) -> None:
        # Shown to the model once, before any tool call — the place to say "read the guide
        # first" and "long work returns a job id".
        assert "get_guide" in (build().instructions or "")

    async def test_calling_before_binding_is_a_loud_error(self) -> None:
        # A tool layer with no app would otherwise fail somewhere deep inside httpx.
        original = client._app
        client._app = None
        try:
            with pytest.raises(RuntimeError, match="bound"):
                await client.call("GET", "/datasets")
        finally:
            client._app = original

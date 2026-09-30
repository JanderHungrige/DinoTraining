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

import asyncio
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
async def running_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[FastAPI]:
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
            "import_coco_dataset",
            "create_dataset",
            "list_folder_images",
            "export_dataset",
            "propose_annotations",
            "save_annotations",
            "run_inference",
            # Doc 91: preparation, the step an assistant would otherwise skip or improvise.
            "inspect_coco_export",
            "audit_dataset",
            "fix_dataset",
            "split_dataset",
            "plan_preparation",
            "save_recipe",
            "list_recipes",
            # Doc 98: fine-tuning any foundation model, with its data requirements.
            "get_finetune_requirements",
            "check_dataset_for",
            "start_finetune",
            # Doc 102: the Training tab's settings and default recipes, for an assistant too.
            "get_training_parameters",
            "create_default_recipe",
            # Doc 110: annotating for SAM 3, and keeping it consistent.
            "get_annotation_targets",
            "list_phrases",
            "add_phrase",
            "set_phrase_status",
            "get_annotation_guideline",
            "set_annotation_guideline",
            # Doc 117/118: which saved pictures are unknown for a class, and the answer
            # "it does not occur there".
            "get_completeness",
            "mark_absent_in_older_pictures",
            # Wave 15.6: trained models' cards, export and MLflow.
            "get_model_card",
            "export_model",
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
        # Doc 91: random video splits inflate scores; class merges are the user's call;
        # a recipe is what makes training use the leak-free split.
        assert "video" in described["split_dataset"]
        assert "Ask before merging" in described["fix_dataset"]
        # Doc 82: an unchecked xyxy export silently lost 162 of 273 boxes.
        assert "inspect_coco_export" in described["import_coco_dataset"]
        assert "recipe_id" in described["train_head"] and "recipe_id" in described["save_recipe"]

    async def test_a_job_starting_tool_points_at_get_job(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Blocking a tool call for four minutes hits a client timeout and loses the run.
        async with running_app(tmp_path, monkeypatch) as app:
            described = await descriptions(app)

        for name in (
            "install_model",
            "train_head",
            "start_finetune",
            "audit_dataset",
            "create_default_recipe",
        ):
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
            listed = await rpc(app, "tools/call", {"name": "list_datasets", "arguments": {}})

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
        # And *why*: the API's own message, not "Error executing tool" (doc 91).
        assert "nope" in str(body["result"]["content"])

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

        assert set(_JOB_PATHS) == {
            "download",
            "training",
            "finetune",
            "audit",
            "foundation-finetune",
            "default-recipe",
        }
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


class TestPreparationTools:
    async def test_the_preparation_tools_reach_the_app_and_refuse_with_reasons(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with running_app(tmp_path, monkeypatch) as app:
            created = await rpc(
                app, "tools/call", {"name": "create_dataset", "arguments": {"name": "Prep"}}
            )
            dataset_id = json.loads(created["result"]["content"][0]["text"])["id"]
            plan = await rpc(
                app,
                "tools/call",
                {
                    "name": "plan_preparation",
                    "arguments": {"dataset_id": dataset_id, "target": "rf-detr-nano"},
                },
            )
            refused = await rpc(
                app,
                "tools/call",
                {
                    "name": "save_recipe",
                    "arguments": {
                        "dataset_id": dataset_id,
                        "name": "first",
                        "target": "rf-detr-nano",
                        "imbalance": "none",
                        "augmentation": "none",
                    },
                },
            )

        assert plan["result"].get("isError") is not True, plan
        planned = json.loads(plan["result"]["content"][0]["text"])
        assert {"targets", "input", "balance", "augmentation"} <= set(planned)
        # No audit yet: the refusal names the step, and reaches the model as a failure.
        assert refused["result"].get("isError") is True
        assert "Audit step" in str(refused["result"])


class TestFinetuneTools:
    async def test_an_assistant_gets_the_same_requirements_and_the_same_refusal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with running_app(tmp_path, monkeypatch) as app:
            requirements = await rpc(
                app,
                "tools/call",
                {"name": "get_finetune_requirements", "arguments": {"finetune_id": "sam3"}},
            )
            created = await rpc(
                app, "tools/call", {"name": "create_dataset", "arguments": {"name": "Empty"}}
            )
            dataset_id = json.loads(created["result"]["content"][0]["text"])["id"]
            refused = await rpc(
                app,
                "tools/call",
                {
                    "name": "start_finetune",
                    "arguments": {
                        "finetune_id": "sam2.1-hiera-small",
                        "dataset_ids": [dataset_id],
                        "name": "x",
                    },
                },
            )

        spec = json.loads(requirements["result"]["content"][0]["text"])
        assert spec["prompt_kind"] == "noun-phrase" and "phrase" in spec["data_format"]
        # The rules the data breaks, in the words the Training tab uses (doc 92).
        assert refused["result"].get("isError") is True
        text = str(refused["result"])
        assert "outline" in text and "Prepare data" in text


class TestTrainingKnobTools:
    """Doc 102: the assistant gets the Training tab's settings and default recipe."""

    async def test_it_reads_a_model_s_settings_with_their_reasons(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with running_app(tmp_path, monkeypatch) as app:
            answer = await rpc(
                app,
                "tools/call",
                {"name": "get_training_parameters", "arguments": {"model_id": "sam3"}},
            )
        body = json.loads(answer["result"]["content"][0]["text"])
        rounds = next(p for p in body["parameters"] if p["key"] == "epochs")
        assert (rounds["label"], rounds["term"], rounds["default"]) == ("Rounds", "epochs", 4)
        assert rounds["why"]

    async def test_a_misspelt_option_is_an_error_that_names_it(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with running_app(tmp_path, monkeypatch) as app:
            refused = await rpc(
                app,
                "tools/call",
                {
                    "name": "start_finetune",
                    "arguments": {
                        "finetune_id": "sam2.1-hiera-small",
                        "dataset_ids": ["x"],
                        "name": "x",
                        "options": {"box_jiter": 0.2},
                    },
                },
            )
        assert refused["result"].get("isError") is True
        assert "box_jiter" in str(refused["result"])

    async def test_it_starts_a_default_recipe_and_names_its_job_kind(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with running_app(tmp_path, monkeypatch) as app:
            created = await rpc(
                app, "tools/call", {"name": "create_dataset", "arguments": {"name": "Empty"}}
            )
            dataset_id = json.loads(created["result"]["content"][0]["text"])["id"]
            started = await rpc(
                app,
                "tools/call",
                {
                    "name": "create_default_recipe",
                    "arguments": {"dataset_id": dataset_id, "model_id": "rf-detr-nano"},
                },
            )
            described = await descriptions(app)
            job = json.loads(started["result"]["content"][0]["text"])
            # Waited out inside the app: a job thread still reading the database when the
            # next test closes the connection segfaults the whole run (found 2026-09-30).
            finished = await _finished(app, job["job_id"])
        assert finished["state"] == "failed"  # an empty dataset has nothing to split
        assert "no images" in finished["message"].lower()
        assert "default-recipe" in described["create_default_recipe"]


async def _finished(app: FastAPI, job_id: str) -> dict[str, Any]:
    for _ in range(200):
        polled = await rpc(
            app,
            "tools/call",
            {"name": "get_job", "arguments": {"job_id": job_id, "kind": "default-recipe"}},
        )
        body: dict[str, Any] = json.loads(polled["result"]["content"][0]["text"])
        if body["state"] not in ("pending", "running"):
            return body
        await asyncio.sleep(0.05)
    raise AssertionError("the default-recipe job did not finish")


class TestAnnotationTools:
    """Doc 110: phrases with variations, checks and the guideline, over MCP."""

    async def test_a_phrase_with_variations_and_a_guideline(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        async with running_app(tmp_path, monkeypatch) as app:
            created = await rpc(
                app, "tools/call", {"name": "create_dataset", "arguments": {"name": "Rails"}}
            )
            dataset_id = json.loads(created["result"]["content"][0]["text"])["id"]
            added = await rpc(
                app,
                "tools/call",
                {
                    "name": "add_phrase",
                    "arguments": {"dataset_id": dataset_id, "text": "signal, light signal"},
                },
            )
            await rpc(
                app,
                "tools/call",
                {
                    "name": "set_annotation_guideline",
                    "arguments": {"dataset_id": dataset_id, "text": "Poles count."},
                },
            )
            guideline = await rpc(
                app,
                "tools/call",
                {"name": "get_annotation_guideline", "arguments": {"dataset_id": dataset_id}},
            )
            described = await descriptions(app)
        phrase = json.loads(added["result"]["content"][0]["text"])
        assert (phrase["text"], phrase["variants"]) == ("signal", ["light signal"])
        assert json.loads(guideline["result"]["content"][0]["text"]) == {"text": "Poles count."}
        # The rules an assistant would otherwise break, in the tool it reads.
        assert "Only checked pictures teach" in described["set_phrase_status"]
        assert "Two to four variations are enough" in described["add_phrase"]

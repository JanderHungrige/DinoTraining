"""The API guide an assistant is handed (doc 63).

Two halves with opposite failure modes, and the tests split the same way.

The **generated** half must not go stale — an endpoint list transcribed by hand is wrong the
first time anyone adds a route, and a confidently wrong list is worse than none. So it is
tested against the app's own schema rather than against a fixture.

The **written** half must not omit the things a schema cannot say. Those are not stylistic:
an assistant that does not know a model must be installed first will call fine-tune and get
a 409 it cannot interpret, and one that does not know the class field is `prompt` will write
a dataset where every class is NULL — silently, which is the doc 31 bug.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.v1.agent_docs import build_guide
from app.docs.reference import render_reference
from app.main import create_app


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def guide(client: TestClient) -> str:
    response = client.get("/api/v1/docs/agent-guide")
    assert response.status_code == 200
    return response.text


class TestTheRoute:
    def test_it_serves_markdown_not_json(self, client: TestClient) -> None:
        # The audience is a language model. JSON of a document is a document nobody can read
        # without unwrapping it first.
        response = client.get("/api/v1/docs/agent-guide")

        assert response.headers["content-type"].startswith("text/markdown")

    def test_it_names_the_file_it_would_be_saved_as(self, client: TestClient) -> None:
        response = client.get("/api/v1/docs/agent-guide")

        assert "dinotraining-api-guide.md" in response.headers["content-disposition"]

    def test_it_is_one_document(self, guide: str) -> None:
        """Not one per workflow. The caller is assembling a prompt, and five fetches to
        build one is five ways to send half of it."""
        for heading in ("## 1. Install a model", "## Endpoint reference"):
            assert heading in guide

    def test_it_fits_a_context_window(self, guide: str) -> None:
        # Not a hard limit, a smell test: a guide that grew to 200 KB has stopped being a
        # thing you paste and become a thing you search, which is a different feature.
        assert len(guide) < 60_000, f"{len(guide)} characters is too long to paste"


class TestTheGeneratedHalf:
    def test_every_route_the_app_serves_appears(self, client: TestClient) -> None:
        """The property that makes generation worth it. Adding a route to `router.py`
        must put it in the guide with no other edit — and this is what proves it."""
        schema = client.get("/openapi.json").json()
        guide = client.get("/api/v1/docs/agent-guide").text

        missing = [path for path in schema["paths"] if path not in guide]
        assert missing == [], f"not in the guide: {missing}"

    def test_it_reports_each_method_separately(self) -> None:
        # `PUT /datasets/{id}/images` and `GET /datasets/{id}/images` are different
        # operations on one path, and an agent needs both.
        rendered = render_reference(
            {
                "paths": {
                    "/thing": {
                        "get": {"summary": "Read it", "tags": ["things"]},
                        "put": {"summary": "Replace it", "tags": ["things"]},
                    }
                }
            }
        )

        assert "`GET /thing`" in rendered
        assert "`PUT /thing`" in rendered

    def test_it_names_the_fields_a_caller_cannot_omit(self) -> None:
        rendered = render_reference(
            {
                "paths": {
                    "/train": {
                        "post": {
                            "summary": "Train",
                            "tags": ["training"],
                            "requestBody": {
                                "content": {
                                    "application/json": {
                                        "schema": {"required": ["backbone_id", "epochs"]}
                                    }
                                }
                            },
                        }
                    }
                }
            }
        )

        assert "backbone_id" in rendered
        assert "epochs" in rendered

    def test_a_ref_body_does_not_break_it(self) -> None:
        """Most real bodies are `$ref`s. Following them would make this a schema walker,
        and the one that already does that correctly is `/openapi.json` — so an
        unresolvable body must degrade to no field list rather than to an exception."""
        rendered = render_reference(
            {
                "paths": {
                    "/thing": {
                        "post": {
                            "summary": "Do it",
                            "tags": ["things"],
                            "requestBody": {
                                "content": {
                                    "application/json": {"schema": {"$ref": "#/x/Thing"}}
                                }
                            },
                        }
                    }
                }
            }
        )

        assert "`POST /thing`" in rendered

    def test_an_empty_schema_is_a_document_not_a_crash(self) -> None:
        assert "Endpoint reference" in render_reference({"paths": {}})


class TestTheWrittenHalf:
    """The things no schema records. Each of these has a real failure behind it."""

    def test_it_states_the_base_url_and_that_it_is_loopback(self, guide: str) -> None:
        # The single most likely agent failure is calling a public host that does not
        # exist. It is the first thing in the document for that reason.
        assert "127.0.0.1:8756/api/v1" in guide
        assert "loopback" in guide

    def test_it_says_paths_are_the_backends_paths(self, guide: str) -> None:
        """An agent that assumes an upload will send bytes to a route that wants a string,
        and read the 422 as a bug in the API."""
        assert "There is no\nupload" in guide or "There is no upload" in guide
        assert "absolute path" in guide

    def test_it_says_long_work_is_polled(self, guide: str) -> None:
        # Otherwise a fine-tune "returns immediately" and the agent reports success on a
        # job that has not started.
        assert "poll" in guide.lower()
        assert 'state` is no longer `running' in guide or "state != " in guide

    def test_it_warns_that_the_class_field_is_prompt(self, guide: str) -> None:
        """Doc 31's bug, and the most expensive one to repeat: sending `text` has pydantic
        drop it, every class lands NULL, and there is no error anywhere."""
        assert "`prompt`, not `text`" in guide

    def test_it_says_a_put_replaces_rather_than_appends(self, guide: str) -> None:
        assert "replaces" in guide.lower() or "not an append" in guide

    def test_it_says_a_model_must_be_installed_before_it_is_used(self, guide: str) -> None:
        assert "Install a model" in guide
        assert "installed" in guide

    def test_it_carries_the_measured_comparison_rather_than_an_opinion(
        self, guide: str
    ) -> None:
        """"Fine-tuning is better" is an opinion an assistant may or may not act on. The
        numbers are what make it choose, and they were measured in this app."""
        assert "0.96" in guide
        assert "0.5" in guide

    def test_it_explains_the_empty_result_a_tiled_head_gives(self, guide: str) -> None:
        # The silent failure. An agent that gets an empty list and reports "no objects
        # found" is wrong in a way nothing else would reveal.
        assert "tiles" in guide
        assert "trained_width" in guide

    def test_the_worked_example_is_the_request_that_prompted_this(self, guide: str) -> None:
        assert "worked example" in guide.lower()
        assert "fine-tune RF-DETR" in guide


class TestBuildGuide:
    def test_recipes_come_before_the_reference(self, client: TestClient) -> None:
        """An assistant given the endpoint list first starts calling things. Given the
        recipes first it has the preconditions before it has the URLs."""
        document = build_guide(client.get("/openapi.json").json())

        assert document.index("## 1. Install a model") < document.index("## Endpoint reference")

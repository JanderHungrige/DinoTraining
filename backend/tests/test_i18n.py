"""German answers by Accept-Language (doc 113): the template matcher and the middleware.

Catalogue coverage (every static text and every audit rule) is in test_i18n_coverage.py.
"""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator, AsyncIterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from httpx import ASGITransport, AsyncClient

from app.i18n.middleware import GermanTextMiddleware, translate_body
from app.i18n.translate import build_catalogue, compile_template, german, translate_text
from app.mcp import client as mcp_client
from tests.datasets_api_testkit import dataset_client

DE = {"Accept-Language": "de-DE,de;q=0.9,en;q=0.8"}


class TestTranslateText:
    def test_a_static_text_is_looked_up_exactly(self) -> None:
        assert translate_text("Leave it", "de") == "So lassen"
        assert translate_text("Leave it", "de-AT") == "So lassen"

    def test_a_template_carries_its_values_into_the_german(self) -> None:
        assert translate_text("Only 12 images", "de") == "Nur 12 Bilder"
        assert (
            translate_text("'pawn' has 120 examples, 'bishop' only 1.", "de")
            == "„pawn“ hat 120 Beispiele, „bishop“ nur 1."
        )

    def test_captured_values_are_not_translated(self) -> None:
        # "Boxes" is a catalogue text; as a class name it stays the user's word.
        assert translate_text("Dataset not found: Boxes", "de") == "Datensatz nicht gefunden: Boxes"
        assert translate_text("Outlines per phrase: Leave it (3).", "de") == (
            "Umrisse pro Phrase: Leave it (3)."
        )

    def test_unmatched_text_passes_through_unchanged(self) -> None:
        for text in ("my dataset", "", "  ", "Only images", "unclear"):
            assert translate_text(text, "de") == text

    def test_english_and_other_languages_are_left_alone(self) -> None:
        assert translate_text("Leave it", "en") == "Leave it"
        assert translate_text("Leave it", "fr") == "Leave it"

    def test_a_number_placeholder_only_takes_a_number(self) -> None:
        assert translate_text("12 found.", "de") == "12 gefunden."
        assert translate_text("Nothing found.", "de") == "Nothing found."

    def test_prose_placeholders_are_translated_inside_the_sentence(self) -> None:
        assert translate_text("Fine-tune SAM 3 needs outlines (masks)", "de") == (
            "„SAM 3 fine-tunen“ braucht Umrisse (Masken)"
        )
        assert translate_text("RF-DETR (nano) is installed", "de") == (
            "RF-DETR (nano) ist installiert"
        )

    def test_an_assembled_refusal_is_translated_sentence_by_sentence(self) -> None:
        refusal = (
            "The dataset has boxes: 3 found. At least 30 images with boxes: 3 images. "
            "Annotate more images. Any size; resized to 1008 px."
        )
        assert translate_text(refusal, "de") == (
            "Der Datensatz hat Boxen: 3 gefunden. Mindestens 30 Bilder mit Boxen: 3 Bilder. "
            "Annotiere mehr Bilder. Jede Größe; wird auf 1008 px verkleinert."
        )

    def test_a_value_does_not_swallow_the_next_sentence(self) -> None:
        text = (
            "Unknown target: sam9. "
            "Look at the preview, and pick another if your pictures are different."
        )
        german_text = translate_text(text, "de")
        assert german_text.startswith("Unbekanntes Ziel: sam9. Sieh dir die Vorschau an")

    def test_a_german_placeholder_must_exist_in_the_english(self) -> None:
        with pytest.raises(ValueError, match="placeholder"):
            compile_template("Only {count} images", "Nur {anzahl} Bilder")

    def test_longer_templates_win_over_shorter_ones(self) -> None:
        catalogue = build_catalogue({"{a} b": "short", "{a} b c": "long {a}"}, {})
        template = next(t for t in catalogue.buckets[""] if t.pattern.fullmatch("x b c"))
        assert template.german == "long {a}"

    def test_every_catalogue_template_compiles(self) -> None:
        catalogue = german()
        assert len(catalogue.exact) > 250
        assert sum(len(b) for b in catalogue.buckets.values()) > 0


class TestTranslateBody:
    def test_only_text_fields_are_translated(self) -> None:
        body = {
            "id": "Leave it",
            "name": "Leave it",
            "path": "Leave it",
            "title": "Leave it",
            "warnings": ["Leave it", 3],
            "nested": [{"reason": "Leave it", "target": "Leave it"}],
        }
        assert translate_body(body, "de") == {
            "id": "Leave it",
            "name": "Leave it",
            "path": "Leave it",
            "title": "So lassen",
            "warnings": ["So lassen", 3],
            "nested": [{"reason": "So lassen", "target": "Leave it"}],
        }


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for ac in dataset_client(tmp_path, monkeypatch):
        yield ac


class TestMiddleware:
    async def test_a_german_request_gets_german_text_and_unchanged_ids(
        self, client: AsyncClient
    ) -> None:
        english = (await client.get("/api/v1/finetune/requirements")).json()
        response = await client.get("/api/v1/finetune/requirements", headers=DE)
        assert response.status_code == 200
        assert int(response.headers["content-length"]) == len(response.content)
        assert "Accept-Language" in response.headers["vary"]
        german_body = response.json()
        sam3 = next(r for r in german_body if r["id"] == "sam3")
        assert sam3["image_sizes"] == "Jede Größe; wird auf 1008 px verkleinert."
        assert sam3["gates"][0].startswith("Auf HuggingFace zugangsbeschränkt")
        for en, de in zip(english, german_body, strict=True):
            for key in ("id", "model_id", "task", "annotation_kind", "prompt_kind"):
                assert en[key] == de[key]

    async def test_english_or_no_header_gets_english(self, client: AsyncClient) -> None:
        for headers in ({}, {"Accept-Language": "en-GB,en;q=0.9,de;q=0.5"}):
            body = (await client.get("/api/v1/training/parameters", headers=headers)).json()
            assert body[0]["parameters"][0]["label"] == "Rounds"

    async def test_the_error_envelope_message_is_translated(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/datasets/nope/annotation-target", headers=DE)
        assert response.status_code == 404
        assert response.json()["error"] == {
            "code": "not_found",
            "message": "Datensatz nicht gefunden: nope",
        }
        english = await client.get("/api/v1/datasets/nope/annotation-target")
        assert english.json()["error"]["message"] == "Dataset not found: nope"

    async def test_a_validation_refusal_arrives_in_german(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/finetune/check", json={}, headers=DE)
        assert response.status_code == 422
        assert response.json()["error"]["message"] == "Die Anfrage ist ungültig."


def _mini_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(GermanTextMiddleware, prefix="/api/v1")

    async def events() -> AsyncIterator[bytes]:
        yield b'data: {"message": "Leave it"}\n\n'

    @app.get("/api/v1/stream")
    async def stream() -> StreamingResponse:
        return StreamingResponse(events(), media_type="text/event-stream")

    @app.get("/api/v1/text")
    async def text() -> JSONResponse:
        return JSONResponse({"message": "Leave it"}, media_type="text/plain")

    @app.get("/elsewhere")
    async def elsewhere() -> dict[str, str]:
        return {"message": "Leave it"}

    return app


class TestPassThrough:
    async def test_streams_non_json_and_other_paths_are_untouched(self) -> None:
        transport = ASGITransport(app=_mini_app())
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            stream = await ac.get("/api/v1/stream", headers=DE)
            assert stream.text == 'data: {"message": "Leave it"}\n\n'
            text = await ac.get("/api/v1/text", headers=DE)
            assert json.loads(text.text) == {"message": "Leave it"}
            other = await ac.get("/elsewhere", headers=DE)
            assert other.json() == {"message": "Leave it"}


class TestMcpStaysEnglish:
    async def test_the_tool_layer_sends_no_language_and_reads_english(
        self, client: AsyncClient
    ) -> None:
        # `client` built the app, and `mount_mcp` bound the tool layer to it.
        requirements = await mcp_client.call("GET", "/finetune/requirements")
        sam3 = next(r for r in requirements if r["id"] == "sam3")
        assert sam3["image_sizes"] == "Any size; resized to 1008 px."
        with pytest.raises(mcp_client.ApiError) as refused:
            await mcp_client.call("GET", "/datasets/nope/annotation-target")
        assert refused.value.message == "Dataset not found: nope"

"""Tests for detector loading and output conversion.

No weights are loaded here — what is exercised is prompt normalisation, the install
gate, and the xyxy → xywh conversion that everything downstream depends on.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from app.core.config import get_settings
from app.ml.detector import (
    ModelNotInstalledError,
    _to_detections,
    clear_cache,
    load_detector,
    normalise_prompt,
)


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    clear_cache()
    yield
    clear_cache()


class TestNormalisePrompt:
    def test_lowercases(self) -> None:
        assert normalise_prompt("A Cat") == "a cat."

    def test_adds_a_trailing_period(self) -> None:
        assert normalise_prompt("a cat") == "a cat."

    def test_keeps_an_existing_period(self) -> None:
        assert normalise_prompt("a cat.") == "a cat."

    def test_preserves_multi_phrase_prompts(self) -> None:
        """Wording is the user's tuning surface; only casing and the separator change."""
        assert normalise_prompt("A Cat. A Dog") == "a cat. a dog."

    def test_strips_surrounding_whitespace(self) -> None:
        assert normalise_prompt("  a cat  ") == "a cat."

    def test_empty_prompt_raises(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            normalise_prompt("   ")


class TestLoadDetector:
    def test_uninstalled_model_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path))
        get_settings.cache_clear()
        with pytest.raises(ModelNotInstalledError):
            load_detector("grounding-dino-tiny")

    def test_unknown_model_raises_lookup_error(self) -> None:
        with pytest.raises(LookupError):
            load_detector("not-a-model")

    def test_a_backbone_is_not_a_detector(self) -> None:
        with pytest.raises(ValueError, match="not a detector"):
            load_detector("dinov2-base")


class FakeTensor(float):
    """Stands in for a torch scalar — floats round-trip through float() the same way."""


def results(boxes: list[list[float]], scores: list[float], labels: list[str]) -> dict[str, Any]:
    return {"boxes": boxes, "scores": scores, "text_labels": labels}


class TestToDetections:
    def test_converts_xyxy_to_xywh(self) -> None:
        found = _to_detections(results([[10, 20, 110, 100]], [0.9], ["a cat"]))
        assert (found[0].x, found[0].y, found[0].w, found[0].h) == (10, 20, 100, 80)

    def test_carries_score_and_text(self) -> None:
        found = _to_detections(results([[0, 0, 10, 10]], [0.8123456], ["a dog"]))
        assert found[0].score == pytest.approx(0.8123, abs=1e-4)
        assert found[0].text == "a dog"

    def test_drops_degenerate_boxes(self) -> None:
        """A zero-area proposal is not a box and would fail the store's CHECK anyway."""
        found = _to_detections(
            results([[10, 10, 10, 50], [0, 0, 20, 20]], [0.9, 0.8], ["a", "b"])
        )
        assert len(found) == 1
        assert found[0].w == 20

    def test_clamps_negative_origins(self) -> None:
        """Models sometimes propose boxes starting slightly off-frame."""
        found = _to_detections(results([[-5, -8, 20, 20]], [0.7], ["a"]))
        assert found[0].x == 0
        assert found[0].y == 0

    def test_handles_multiple_boxes(self) -> None:
        found = _to_detections(
            results([[0, 0, 5, 5], [10, 10, 20, 20], [1, 1, 4, 4]], [0.9, 0.8, 0.7], ["a"] * 3)
        )
        assert len(found) == 3

    def test_empty_results_yield_no_detections(self) -> None:
        assert _to_detections(results([], [], [])) == []

    def test_falls_back_to_labels_key(self) -> None:
        """transformers renamed text_labels; both shapes must work."""
        found = _to_detections({"boxes": [[0, 0, 5, 5]], "scores": [0.5], "labels": ["a cat"]})
        assert found[0].text == "a cat"

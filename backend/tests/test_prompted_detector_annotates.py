"""Grounding DINO can *propose* annotations, not only be looked at (doc 66, bug found in doc 71).

Doc 66 made Grounding DINO a foundation model and verified that the Generator showed its
prompt field. Nobody pressed Propose: `propose_foundation_boxes` dispatched on
ConceptSegmenter and RfDetrModel only, so the Generator and the Studio refused it with
"does not predict boxes" — about the one model in the catalogue that predicts nothing else.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.core.config import get_settings
from app.ml.annotators.foundation import (
    FoundationCannotAnnotateError,
    propose_foundation_boxes,
)
from app.ml.detector import Detection
from app.ml.foundation.build import reset_cache
from app.ml.foundation.prompt_detect import PromptedDetector
from app.ml.foundation.registry import get_foundation


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_cache()


@pytest.fixture
def grounding_dino(monkeypatch: pytest.MonkeyPatch) -> PromptedDetector:
    spec = get_foundation("grounding-dino-tiny")
    assert spec is not None
    calls: list[tuple[str, float]] = []

    def fake_detect(_model: object, _image: Image.Image, prompt: str, *, box_threshold: float):
        calls.append((prompt, box_threshold))
        return [
            Detection(x=10.0, y=5.0, w=20.0, h=10.0, score=0.81, text="a chess piece"),
            Detection(x=40.0, y=15.0, w=8.0, h=12.0, score=0.44, text="a board"),
        ]

    monkeypatch.setattr("app.ml.foundation.prompt_detect.load_detector", lambda _id: object())
    monkeypatch.setattr("app.ml.foundation.prompt_detect.detect", fake_detect)
    model = PromptedDetector(spec)
    model.calls = calls  # type: ignore[attr-defined]
    monkeypatch.setattr(
        "app.ml.annotators.foundation.build_foundation", lambda *a, **k: model
    )
    return model


def test_grounding_dino_proposes_boxes_named_by_the_matched_phrase(
    grounding_dino: PromptedDetector,
) -> None:
    image = Image.new("RGB", (64, 48))
    proposals = propose_foundation_boxes(
        image, "grounding-dino-tiny", concept="a chess piece. a board.", score_threshold=0.3
    )

    assert [p.box.prompt for p in proposals] == ["a chess piece", "a board"]
    assert (proposals[0].box.x, proposals[0].box.y, proposals[0].box.w, proposals[0].box.h) == (
        10.0,
        5.0,
        20.0,
        10.0,
    )
    assert proposals[0].box.score == pytest.approx(0.81)
    assert proposals[0].box.provenance == "foundation-model"
    assert proposals[0].mask is None
    # The concept reached the model, with the user's threshold.
    assert grounding_dino.calls == [("a chess piece. a board.", 0.3)]  # type: ignore[attr-defined]


def test_the_producer_records_which_model_and_which_prompt(
    grounding_dino: PromptedDetector,
) -> None:
    proposals = propose_foundation_boxes(
        Image.new("RGB", (64, 48)), "grounding-dino-tiny", concept="a chess piece."
    )
    assert proposals[0].box.producer.id == "grounding-dino-tiny"
    assert "a chess piece" in proposals[0].box.producer.label


def test_an_empty_prompt_is_refused_rather_than_proposing_nothing(
    grounding_dino: PromptedDetector,
) -> None:
    # PromptedDetector returns an empty prediction for "", which here would read as "this
    # image has nothing in it" — and autoplay would record it as empty and move on.
    with pytest.raises(FoundationCannotAnnotateError, match="what you are looking for"):
        propose_foundation_boxes(Image.new("RGB", (64, 48)), "grounding-dino-tiny", concept=" ")

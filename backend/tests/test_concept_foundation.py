"""Concept-prompted segmenters as foundation models (doc 45).

Grounded SAM was reachable only from the Dataset Generator. What is worth pinning is not
that it is now listed, but the three things that fail *quietly*: an install state computed
from one model when the pipeline needs several, a concept silently dropped so the model
segments nothing and reports success, and the mask/box split going to the wrong surfaces.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.core.config import get_settings
from app.datasets.rle import rle_encode
from app.ml.annotators.base import MaskProposal
from app.ml.annotators.foundation import (
    FoundationCannotAnnotateError,
    propose_foundation_boxes,
)
from app.ml.foundation.build import build_foundation, reset_cache
from app.ml.foundation.concept import ConceptSegmenter
from app.ml.foundation.registry import get_foundation


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_cache()


def _mask(height: int, width: int, box: tuple[int, int, int, int]) -> list[int]:
    x, y, w, h = box
    array = np.zeros((height, width), dtype=bool)
    array[y : y + h, x : x + w] = True
    return rle_encode(array)[0]


def _proposal(concept: str, box: tuple[int, int, int, int], score: float = 0.9) -> MaskProposal:
    return MaskProposal(
        counts=_mask(40, 60, box),
        size=(40, 60),
        box=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
        score=score,
        concept=concept,
    )


class _StubAnnotator:
    """Stands in for Grounded SAM. Records what it was asked, returns what it was given."""

    annotator_id = "grounded-sam"

    def __init__(self, proposals: list[MaskProposal]) -> None:
        self._proposals = proposals
        self.calls: list[tuple[str, float]] = []

    def propose(
        self, image: Image.Image, concept: str, *, threshold: float = 0.3
    ) -> list[MaskProposal]:
        self.calls.append((concept, threshold))
        return self._proposals


@pytest.fixture
def segmenter(monkeypatch: pytest.MonkeyPatch) -> ConceptSegmenter:
    spec = get_foundation("grounded-sam")
    assert spec is not None
    stub = _StubAnnotator([_proposal("cat", (5, 5, 10, 10)), _proposal("dog", (30, 20, 12, 8))])
    monkeypatch.setattr("app.ml.foundation.concept.build_annotator", lambda _id: stub)
    model = ConceptSegmenter(spec)
    model.stub = stub  # type: ignore[attr-defined]
    return model


class TestItIsRegisteredAsAFoundationModel:
    def test_grounded_sam_is_in_the_catalogue(self) -> None:
        spec = get_foundation("grounded-sam")
        assert spec is not None and spec.render_hint == "masks"

    def test_it_declares_that_it_needs_a_concept(self) -> None:
        # The picker shows a concept field off this flag alone. Without it the user gets a
        # model that returns nothing and no indication why.
        spec = get_foundation("grounded-sam")
        assert spec is not None and spec.takes_concept is True

    def test_a_detector_does_not(self) -> None:
        spec = get_foundation("rf-detr-nano")
        assert spec is not None and spec.takes_concept is False

    def test_building_it_gives_a_concept_segmenter(self) -> None:
        assert isinstance(build_foundation("grounded-sam"), ConceptSegmenter)


class TestThePredictionTheViewerDraws:
    def test_it_reports_masks_so_the_overlay_registry_needs_nothing_new(
        self, segmenter: ConceptSegmenter
    ) -> None:
        prediction = segmenter.predict(Image.new("RGB", (60, 40)), "cat. dog.")
        assert prediction.render_hint == "masks"
        assert set(prediction.payload) >= {"mask_png", "present_classes", "height", "width"}

    def test_class_zero_is_background_not_the_first_concept(
        self, segmenter: ConceptSegmenter
    ) -> None:
        """Off by one here paints every unmatched pixel as the first concept — a full-frame
        mask that looks like an over-eager model rather than an indexing bug."""
        prediction = segmenter.predict(Image.new("RGB", (60, 40)), "cat. dog.")
        assert prediction.class_names == ("background", "cat", "dog")

    def test_each_concept_gets_its_own_index(self, segmenter: ConceptSegmenter) -> None:
        prediction = segmenter.predict(Image.new("RGB", (60, 40)), "cat. dog.")
        assert prediction.payload["present_classes"] == [0, 1, 2]

    def test_an_empty_concept_returns_an_empty_prediction_rather_than_running(
        self, segmenter: ConceptSegmenter
    ) -> None:
        # The state before the user has typed anything. Running a two-model pipeline over
        # an empty string is seconds of work to produce nothing.
        prediction = segmenter.predict(Image.new("RGB", (60, 40)), "   ")
        assert prediction.payload["present_classes"] == [0]
        assert segmenter.stub.calls == []  # type: ignore[attr-defined]

    def test_the_threshold_reaches_the_annotator(self, segmenter: ConceptSegmenter) -> None:
        segmenter.predict(Image.new("RGB", (60, 40)), "cat", 0.55)
        assert segmenter.stub.calls == [("cat", 0.55)]  # type: ignore[attr-defined]

    def test_two_proposals_of_one_concept_share_an_index(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        spec = get_foundation("grounded-sam")
        assert spec is not None
        stub = _StubAnnotator([_proposal("cat", (1, 1, 5, 5)), _proposal("cat", (20, 20, 5, 5))])
        monkeypatch.setattr("app.ml.foundation.concept.build_annotator", lambda _id: stub)
        prediction = ConceptSegmenter(spec).predict(Image.new("RGB", (60, 40)), "cat")
        assert prediction.class_names == ("background", "cat")
        assert prediction.payload["present_classes"] == [0, 1]


class TestTheBoxesTheStudioReviews:
    def test_it_proposes_boxes_from_a_concept_segmenter(
        self, monkeypatch: pytest.MonkeyPatch, segmenter: ConceptSegmenter
    ) -> None:
        monkeypatch.setattr(
            "app.ml.annotators.foundation.build_foundation", lambda *a, **k: segmenter
        )
        boxes = propose_foundation_boxes(
            Image.new("RGB", (60, 40)), "grounded-sam", concept="cat. dog."
        )
        assert len(boxes) == 2

    def test_the_matched_phrase_becomes_the_class(
        self, monkeypatch: pytest.MonkeyPatch, segmenter: ConceptSegmenter
    ) -> None:
        """A reviewer should not be able to tell a concept segmenter's box from a
        detector's except by looking at where it says it came from."""
        monkeypatch.setattr(
            "app.ml.annotators.foundation.build_foundation", lambda *a, **k: segmenter
        )
        proposals = propose_foundation_boxes(
            Image.new("RGB", (60, 40)), "grounded-sam", concept="cat. dog."
        )
        assert [p.box.prompt for p in proposals] == ["cat", "dog"]

    def test_the_mask_rides_along_with_its_box(
        self, monkeypatch: pytest.MonkeyPatch, segmenter: ConceptSegmenter
    ) -> None:
        """Doc 61. The box is the mask's extents, so taking only the box meant every
        Studio run computed a segmentation and dropped it on the floor."""
        monkeypatch.setattr(
            "app.ml.annotators.foundation.build_foundation", lambda *a, **k: segmenter
        )
        proposals = propose_foundation_boxes(
            Image.new("RGB", (60, 40)), "grounded-sam", concept="cat. dog."
        )

        assert all(p.mask is not None for p in proposals)
        # The RLE covers the frame the model saw, not the box it implies.
        assert proposals[0].mask is not None
        assert proposals[0].mask.size == (40, 60)

    def test_provenance_says_a_foundation_model_made_it(
        self, monkeypatch: pytest.MonkeyPatch, segmenter: ConceptSegmenter
    ) -> None:
        monkeypatch.setattr(
            "app.ml.annotators.foundation.build_foundation", lambda *a, **k: segmenter
        )
        proposals = propose_foundation_boxes(
            Image.new("RGB", (60, 40)), "grounded-sam", concept="cat"
        )
        assert proposals[0].box.provenance == "foundation-model"
        assert proposals[0].box.producer is not None
        assert "cat" in proposals[0].box.producer.label

    def test_no_concept_is_refused_rather_than_silently_returning_nothing(
        self, monkeypatch: pytest.MonkeyPatch, segmenter: ConceptSegmenter
    ) -> None:
        # Nothing-found and nothing-asked look identical on a canvas. They must not.
        monkeypatch.setattr(
            "app.ml.annotators.foundation.build_foundation", lambda *a, **k: segmenter
        )
        with pytest.raises(FoundationCannotAnnotateError, match="concept"):
            propose_foundation_boxes(Image.new("RGB", (60, 40)), "grounded-sam", concept="  ")

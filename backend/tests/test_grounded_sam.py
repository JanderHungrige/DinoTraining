"""Tests for Grounded SAM — Grounding DINO boxes turned into SAM 2.1 masks.

Both models are stubbed: loading them is ~850 MB and the join is what has the decisions in
it. What the stubs cannot prove — that the real SAM batches N boxes into N masks, and that
its output tensors live on MPS — was measured against the real checkpoints before this
module was written, and `_to_numpy` exists because of it. The end-to-end run against real
weights is recorded in doc 27.
"""

from __future__ import annotations

import numpy as np
import pytest

from app.datasets.rle import rle_decode
from app.ml.annotators.build import (
    AnnotatorUnavailableError,
    build_annotator,
    implemented_annotator_ids,
)
from app.ml.annotators.grounded_sam import GroundedSamAnnotator, _to_xyxy
from app.ml.annotators.registry import (
    GROUNDED_SAM,
    GROUNDED_SAM_BASE,
    GROUNDED_SAM_LARGE,
    SAM3,
    get_annotator,
)
from app.ml.detector import Detection

#: One box, so the pipeline reaches its segmenter stage. Below the detector threshold it
#: would short-circuit and never load SAM at all.
_DETECTION = Detection(x=1.0, y=2.0, w=3.0, h=4.0, score=0.9, text="a cat")


class _Image:
    """Enough of a PIL image for the annotator; the stubs never decode it."""

    width = 40
    height = 30


def block(x0: int, y0: int, x1: int, y1: int, height: int = 30, width: int = 40) -> np.ndarray:
    mask = np.zeros((height, width), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


@pytest.fixture
def stub(monkeypatch: pytest.MonkeyPatch):
    """Patch both stages and record what the segmenter was asked for."""
    calls: dict[str, object] = {}

    def fake_detect(detector, image, prompt, box_threshold=0.3, **kwargs):
        calls["prompt"] = prompt
        calls["threshold"] = box_threshold
        return calls.get("detections", [])

    def fake_segment(segmenter, image, boxes):
        calls["boxes"] = boxes
        return calls.get("masks", np.zeros((0, 30, 40), dtype=bool)), calls.get("ious", [])

    monkeypatch.setattr("app.ml.annotators.grounded_sam.load_detector", lambda *a: object())
    monkeypatch.setattr("app.ml.annotators.grounded_sam.load_segmenter", lambda *a: object())
    monkeypatch.setattr("app.ml.annotators.grounded_sam.detect", fake_detect)
    monkeypatch.setattr("app.ml.annotators.grounded_sam.segment_boxes", fake_segment)
    return calls


class TestPipeline:
    def test_a_concept_reaches_grounding_dino(self, stub: dict) -> None:
        GroundedSamAnnotator().propose(_Image(), "a bolt", threshold=0.4)
        assert stub["prompt"] == "a bolt"
        assert stub["threshold"] == 0.4

    def test_detected_boxes_become_sam_prompts(self, stub: dict) -> None:
        stub["detections"] = [Detection(x=10, y=5, w=20, h=15, score=0.9, text="bolt")]
        stub["masks"] = np.stack([block(10, 5, 30, 20)])
        stub["ious"] = [1.0]

        GroundedSamAnnotator().propose(_Image(), "a bolt")

        # xywh in, xyxy out — the one place that conversion happens.
        assert stub["boxes"] == [(10.0, 5.0, 30.0, 20.0)]

    def test_it_returns_a_mask_per_detection(self, stub: dict) -> None:
        stub["detections"] = [
            Detection(x=0, y=0, w=10, h=10, score=0.9, text="bolt"),
            Detection(x=20, y=10, w=10, h=10, score=0.8, text="nut"),
        ]
        stub["masks"] = np.stack([block(0, 0, 10, 10), block(20, 10, 30, 20)])
        stub["ious"] = [1.0, 1.0]

        proposals = GroundedSamAnnotator().propose(_Image(), "a bolt. a nut.")
        assert len(proposals) == 2

    def test_the_rle_round_trips_to_the_mask(self, stub: dict) -> None:
        original = block(10, 5, 30, 20)
        stub["detections"] = [Detection(x=10, y=5, w=20, h=15, score=0.9, text="bolt")]
        stub["masks"] = np.stack([original])
        stub["ious"] = [1.0]

        proposal = GroundedSamAnnotator().propose(_Image(), "a bolt")[0]
        assert np.array_equal(rle_decode(proposal.counts, proposal.size), original)

    def test_the_bounding_box_is_derived_from_the_mask_not_the_prompt(
        self, stub: dict
    ) -> None:
        """SAM often tightens a loose box; the stored bbox must describe the mask."""
        stub["detections"] = [Detection(x=0, y=0, w=40, h=30, score=0.9, text="bolt")]
        stub["masks"] = np.stack([block(10, 5, 20, 15)])
        stub["ious"] = [1.0]

        proposal = GroundedSamAnnotator().propose(_Image(), "a bolt")[0]
        assert proposal.box == (10.0, 5.0, 10.0, 10.0)

    def test_the_matched_phrase_travels_with_each_mask(self, stub: dict) -> None:
        """A prompt of "a cat. a dog." yields per-box phrases; the reviewer needs those."""
        stub["detections"] = [
            Detection(x=0, y=0, w=10, h=10, score=0.9, text="cat"),
            Detection(x=20, y=10, w=10, h=10, score=0.8, text="dog"),
        ]
        stub["masks"] = np.stack([block(0, 0, 10, 10), block(20, 10, 30, 20)])
        stub["ious"] = [1.0, 1.0]

        concepts = [p.concept for p in GroundedSamAnnotator().propose(_Image(), "a cat. a dog.")]
        assert concepts == ["cat", "dog"]

    def test_the_score_combines_concept_match_and_mask_quality(self, stub: dict) -> None:
        stub["detections"] = [Detection(x=0, y=0, w=10, h=10, score=0.8, text="bolt")]
        stub["masks"] = np.stack([block(0, 0, 10, 10)])
        stub["ious"] = [0.5]

        assert GroundedSamAnnotator().propose(_Image(), "a bolt")[0].score == 0.4


class TestDegenerateCases:
    def test_no_detections_means_no_segmentation_at_all(self, stub: dict) -> None:
        """Prompting SAM with nothing would ask it to segment the whole frame."""
        stub["detections"] = []
        assert GroundedSamAnnotator().propose(_Image(), "a unicorn") == []
        assert "boxes" not in stub, "the segmenter must not have been called"

    def test_an_empty_mask_is_dropped_with_its_box(self, stub: dict) -> None:
        stub["detections"] = [
            Detection(x=0, y=0, w=10, h=10, score=0.9, text="bolt"),
            Detection(x=20, y=10, w=10, h=10, score=0.8, text="nut"),
        ]
        stub["masks"] = np.stack([np.zeros((30, 40), dtype=bool), block(20, 10, 30, 20)])
        stub["ious"] = [1.0, 1.0]

        proposals = GroundedSamAnnotator().propose(_Image(), "a bolt. a nut.")

        # The survivor must be the *nut* — dropping a mask without dropping its box would
        # attribute every later mask to the wrong detection.
        assert len(proposals) == 1
        assert proposals[0].concept == "nut"

    def test_fewer_masks_than_prompts_stops_rather_than_mispairing(
        self, stub: dict
    ) -> None:
        stub["detections"] = [
            Detection(x=0, y=0, w=10, h=10, score=0.9, text="bolt"),
            Detection(x=20, y=10, w=10, h=10, score=0.8, text="nut"),
        ]
        stub["masks"] = np.stack([block(0, 0, 10, 10)])
        stub["ious"] = [1.0]

        proposals = GroundedSamAnnotator().propose(_Image(), "a bolt. a nut.")
        assert len(proposals) == 1
        assert proposals[0].concept == "bolt"


class TestConversion:
    def test_xywh_becomes_xyxy(self) -> None:
        assert _to_xyxy(Detection(x=10, y=20, w=30, h=40, score=1.0, text="x")) == (
            10.0,
            20.0,
            40.0,
            60.0,
        )


class TestBuilder:
    def test_grounded_sam_is_implemented(self) -> None:
        assert build_annotator(GROUNDED_SAM).annotator_id == GROUNDED_SAM

    def test_every_tier_reports_its_own_id(self) -> None:
        """`annotator_id` was a class attribute while one tier existed. Left that way, all
        three would call themselves `grounded-sam` — and the mask output records it."""
        for tier in (GROUNDED_SAM, GROUNDED_SAM_BASE, GROUNDED_SAM_LARGE):
            assert build_annotator(tier).annotator_id == tier

    def test_a_tier_loads_the_weights_its_catalogue_row_names(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The failure this rules out is the quiet one: a variant that runs perfectly well
        on the default weights, so the masks look fine, the timings look fine, and the
        gigabyte you downloaded is never touched."""
        loaded: dict[str, str | None] = {}

        def fake_load_detector(model_id=None):
            loaded["detector"] = model_id
            return object()

        def fake_load_segmenter(model_id=None):
            loaded["segmenter"] = model_id
            return object()

        monkeypatch.setattr(
            "app.ml.annotators.grounded_sam.load_detector", fake_load_detector
        )
        monkeypatch.setattr(
            "app.ml.annotators.grounded_sam.load_segmenter", fake_load_segmenter
        )
        monkeypatch.setattr(
            "app.ml.annotators.grounded_sam.detect", lambda *a, **k: [_DETECTION]
        )
        monkeypatch.setattr(
            "app.ml.annotators.grounded_sam.segment_boxes",
            lambda *a: (np.zeros((1, 30, 40), dtype=bool), [0.9]),
        )

        build_annotator(GROUNDED_SAM_LARGE).propose(_Image(), "a cat")

        spec = get_annotator(GROUNDED_SAM_LARGE)
        assert spec is not None
        assert (loaded["detector"], loaded["segmenter"]) == spec.model_ids

    def test_the_default_tier_still_loads_the_default_weights(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """It passes its ids explicitly now rather than falling through to the loaders'
        defaults. Same two models either way — this pins that they did not drift apart."""
        spec = get_annotator(GROUNDED_SAM)
        assert spec is not None
        from app.ml.detector import DEFAULT_DETECTOR
        from app.ml.segmenter import DEFAULT_SEGMENTER

        assert spec.model_ids == (DEFAULT_DETECTOR, DEFAULT_SEGMENTER)

    def test_an_unknown_id_is_a_lookup_error(self) -> None:
        with pytest.raises(LookupError):
            build_annotator("not-an-annotator")

    def test_sam3_is_implemented(self) -> None:
        assert build_annotator(SAM3).annotator_id == SAM3

    def test_a_catalogued_but_unbuilt_annotator_is_distinguished(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two different answers: a caller mistake, and a feature that has not shipped.

        Every catalogue entry is implemented today, so the unbuilt case is simulated. The
        distinction still has to hold — the next annotator added will be catalogued before
        it is built, exactly as SAM 3 was.
        """
        monkeypatch.setattr("app.ml.annotators.build._BUILDERS", {})
        with pytest.raises(AnnotatorUnavailableError, match="cannot be run yet"):
            build_annotator(SAM3)

    def test_the_implemented_set_is_a_subset_of_the_catalogue(self) -> None:
        from app.ml.annotators.registry import ANNOTATORS

        assert implemented_annotator_ids() <= set(ANNOTATORS)

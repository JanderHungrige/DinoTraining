"""Tests for the SAM 3 annotator — stubbed, and honest about what that cannot prove.

SAM 3 is gated behind Meta's manual approval and is 3.2 GB, so these tests stub the model.
What a stub *can* prove is the pipeline: that a concept reaches the processor as text, that
instances become proposals, that degenerate masks are dropped with their scores, and that
nothing here ever triggers a download.

What it cannot prove is what SAM 2 taught in doc 27 — exact output shapes, and tensors
arriving on the model's device. Both need a real run, which waits on the user's own
download. Recorded in doc 30's known_issues rather than glossed.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pytest
import torch

from app.ml.annotators.build import build_annotator
from app.ml.annotators.registry import SAM3
from app.ml.annotators.sam3 import Sam3Annotator, _to_proposals, segment_concept
from app.ml.errors import ModelNotInstalledError
from app.ml.segmenter import Segmenter


class _Image:
    width = 40
    height = 30


def block(x0: int, y0: int, x1: int, y1: int) -> np.ndarray:
    mask = np.zeros((30, 40), dtype=bool)
    mask[y0:y1, x0:x1] = True
    return mask


class _StubProcessor:
    """Records what it was asked for and returns a fixed instance dict."""

    def __init__(self, instances: dict[str, Any]) -> None:
        self.instances = instances
        self.seen: dict[str, Any] = {}

    def __call__(self, images: object, text: str, return_tensors: str) -> Any:  # noqa: ANN401
        self.seen["text"] = text
        return _StubInputs()

    def post_process_instance_segmentation(
        self, outputs: object, threshold: float, target_sizes: list[tuple[int, int]]
    ) -> list[dict[str, Any]]:
        self.seen["threshold"] = threshold
        self.seen["target_sizes"] = target_sizes
        return [self.instances]


class _StubInputs(dict):  # type: ignore[type-arg]
    def to(self, device: str) -> _StubInputs:
        return self


def stub_segmenter(instances: dict[str, Any]) -> tuple[Segmenter, _StubProcessor]:
    processor = _StubProcessor(instances)
    return (
        Segmenter(model_id="sam3", device="cpu", processor=processor, model=lambda **_: None),
        processor,
    )


class TestPrompting:
    def test_the_concept_goes_in_as_text(self) -> None:
        """The whole difference from Grounded SAM: no detector stage, text straight in."""
        segmenter, processor = stub_segmenter({"scores": torch.tensor([]), "masks": []})
        segment_concept(segmenter, _Image(), "a red circle", 0.3)
        assert processor.seen["text"] == "a red circle"

    def test_the_threshold_and_image_size_are_passed_through(self) -> None:
        segmenter, processor = stub_segmenter({"scores": torch.tensor([]), "masks": []})
        segment_concept(segmenter, _Image(), "a bolt", 0.7)
        assert processor.seen["threshold"] == 0.7
        # (height, width) — the order transformers documents, and easy to invert.
        assert processor.seen["target_sizes"] == [(30, 40)]

    def test_an_empty_concept_is_refused(self) -> None:
        """Prompting SAM 3 with nothing asks it to segment nothing in particular."""
        segmenter, _ = stub_segmenter({"scores": torch.tensor([]), "masks": []})
        with pytest.raises(ValueError, match="concept is required"):
            segment_concept(segmenter, _Image(), "   ", 0.3)


class TestProposals:
    def test_instances_become_proposals(self) -> None:
        instances = {
            "scores": torch.tensor([0.9, 0.8]),
            "masks": torch.tensor(np.stack([block(0, 0, 10, 10), block(20, 10, 30, 20)])),
        }
        proposals = _to_proposals(instances, "a bolt")
        assert len(proposals) == 2
        assert [p.score for p in proposals] == [0.9, 0.8]

    def test_every_proposal_carries_the_concept(self) -> None:
        """One concept per call, unlike Grounded SAM's per-box matched phrase."""
        instances = {
            "scores": torch.tensor([0.9]),
            "masks": torch.tensor(np.stack([block(0, 0, 10, 10)])),
        }
        assert _to_proposals(instances, "a bolt")[0].concept == "a bolt"

    def test_the_box_is_derived_from_the_mask(self) -> None:
        instances = {
            "scores": torch.tensor([0.9]),
            "masks": torch.tensor(np.stack([block(10, 5, 20, 15)])),
        }
        assert _to_proposals(instances, "a bolt")[0].box == (10.0, 5.0, 10.0, 10.0)

    def test_an_empty_mask_is_dropped_with_its_score(self) -> None:
        instances = {
            "scores": torch.tensor([0.9, 0.8]),
            "masks": torch.tensor(
                np.stack([np.zeros((30, 40), dtype=bool), block(20, 10, 30, 20)])
            ),
        }
        proposals = _to_proposals(instances, "a bolt")
        assert len(proposals) == 1
        # The survivor must keep ITS OWN score, not inherit the dropped one.
        assert proposals[0].score == 0.8

    def test_no_instances_is_an_empty_list(self) -> None:
        assert _to_proposals({"scores": torch.tensor([]), "masks": []}, "a unicorn") == []

    def test_a_singleton_candidate_axis_is_squeezed(self) -> None:
        """SAM 2 returns (N, 1, H, W); guard against SAM 3 doing the same."""
        instances = {
            "scores": torch.tensor([0.9]),
            "masks": torch.tensor(np.stack([block(0, 0, 10, 10)])[:, None]),
        }
        assert len(_to_proposals(instances, "a bolt")) == 1


class TestNeverDownloads:
    def test_proposing_without_the_model_installed_raises_rather_than_fetching(
        self, tmp_path: object, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """3.2 GB must never be pulled by a keystroke. The admin tab owns that."""
        monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path))
        from app.core.config import get_settings

        get_settings.cache_clear()
        with pytest.raises(ModelNotInstalledError):
            Sam3Annotator().propose(_Image(), "a bolt")  # type: ignore[arg-type]
        get_settings.cache_clear()


class TestRegistration:
    def test_sam3_is_now_buildable(self) -> None:
        assert build_annotator(SAM3).annotator_id == SAM3

    def test_both_annotators_are_implemented(self) -> None:
        from app.ml.annotators.build import implemented_annotator_ids
        from app.ml.annotators.registry import ANNOTATORS

        assert implemented_annotator_ids() == set(ANNOTATORS)

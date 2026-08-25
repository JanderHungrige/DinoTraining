"""Tests for deriving training targets from Wave 1's box annotations.

Each label carries a meaning the derivation must respect: `negative` means the user
said "not an object" (so it is background), `unclear` means they could not decide (so
it must be ignored, not forced to background).
"""

from __future__ import annotations

from app.datasets.models import Box
from app.ml.training.samples import (
    UNNAMED_CLASS,
    SampleSet,
    TrainingSample,
    build_class_vocabulary,
    samples_for_task,
)


def box(label: str = "positive", prompt: str | None = "a cat", **kwargs: object) -> Box:
    defaults: dict[str, object] = {
        "label": label,
        "provenance": "grounding-dino",
        "prompt": prompt,
        "x": 10.0,
        "y": 10.0,
        "w": 20.0,
        "h": 20.0,
    }
    defaults.update(kwargs)
    return Box(**defaults)  # type: ignore[arg-type]


def annotation(boxes: list[Box], path: str = "/img.png") -> tuple[int, str, int, int, list[Box]]:
    return (1, path, 200, 200, boxes)


class TestClassVocabulary:
    def test_collects_distinct_positive_prompts(self) -> None:
        vocab = build_class_vocabulary(
            [annotation([box(prompt="a cat"), box(prompt="a dog"), box(prompt="a cat")])]
        )
        assert vocab == ("a cat", "a dog")

    def test_is_sorted_for_determinism(self) -> None:
        """A class order that shifts between runs makes saved weights uninterpretable."""
        forward = build_class_vocabulary([annotation([box(prompt="zebra"), box(prompt="ant")])])
        reverse = build_class_vocabulary([annotation([box(prompt="ant"), box(prompt="zebra")])])
        assert forward == reverse == ("ant", "zebra")

    def test_ignores_negative_and_unclear_boxes(self) -> None:
        vocab = build_class_vocabulary(
            [annotation([box(label="negative", prompt="a fox"),
                         box(label="unclear", prompt="a wolf"),
                         box(label="positive", prompt="a cat")])]
        )
        assert vocab == ("a cat",)

    def test_normalises_case_and_trailing_period(self) -> None:
        vocab = build_class_vocabulary([annotation([box(prompt="A Cat."), box(prompt="a cat")])])
        assert vocab == ("a cat",)

    def test_promptless_positive_gets_a_usable_class(self) -> None:
        assert build_class_vocabulary([annotation([box(prompt=None)])]) == (UNNAMED_CLASS,)

    def test_no_positives_yields_empty_vocabulary(self) -> None:
        assert build_class_vocabulary([annotation([box(label="negative")])]) == ()


class TestSamplesForTask:
    def make(self, samples: list[TrainingSample]) -> SampleSet:
        return SampleSet(samples=samples, class_names=("a cat", "a dog"))

    def test_classification_drops_images_without_a_single_class(self) -> None:
        sample_set = self.make(
            [
                TrainingSample(path="a", width=10, height=10, image_class=0),
                TrainingSample(path="b", width=10, height=10, image_class=None),
            ]
        )
        assert [s.path for s in samples_for_task(sample_set, "classification")] == ["a"]

    def test_detection_keeps_background_only_images(self) -> None:
        """An image with no positives is real supervision for a detector, not an empty."""
        sample_set = self.make(
            [
                TrainingSample(path="a", width=10, height=10, targets=((0, 1.0, 1.0, 2.0, 2.0),)),
                TrainingSample(path="b", width=10, height=10, targets=()),
            ]
        )
        assert len(samples_for_task(sample_set, "detection")) == 2

    def test_segmentation_drops_what_nobody_segmented(self) -> None:
        """A box-annotated image in a mixed dataset is not an empty segmentation — it is
        an image no segmenter ever looked at, and training on it teaches the model that
        whatever is in it is background."""
        sample_set = self.make(
            [
                TrainingSample(path="a", width=10, height=10, segmented=True),
                TrainingSample(path="b", width=10, height=10, targets=((0, 1.0, 1.0, 2.0, 2.0),)),
            ]
        )
        assert [s.path for s in samples_for_task(sample_set, "segmentation")] == ["a"]

    def test_segmentation_keeps_an_image_whose_masks_were_all_rejected(self) -> None:
        """The other half of the same rule. A reviewer who rejected every mask said the
        frame is background, which is real supervision — and is why a rejected mask is
        stored as a `negative` rather than deleted."""
        sample_set = self.make(
            [TrainingSample(path="a", width=10, height=10, masks=(), segmented=True)]
        )
        assert len(samples_for_task(sample_set, "segmentation")) == 1

"""RF-DETR as a foundation detector (doc 41).

Two things carry real risk here and get most of the attention:

* **the coordinate convention** — the processor returns xyxy and everything downstream
  speaks xywh, so a missed conversion reads a corner as a size and draws boxes that are
  plausibly wrong rather than obviously wrong;
* **the aligned triples** — boxes, scores and classes are read positionally, so dropping
  one from a single array is a silent mislabel.

The model itself is exercised against real weights in Phase 7b, not here.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.foundation.build import build_foundation, reset_cache
from app.ml.foundation.detect import RfDetrModel, _as_xywh
from app.ml.foundation.registry import all_foundations, get_foundation
from app.ml.inference.payloads import MAX_DISPLAY_BOXES, source_boxes_payload
from app.ml.inference.results import Prediction
from app.ml.registry import get_model


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    reset_cache()


class TestTheRegistryOffersDetectors:
    def test_rf_detr_is_offered(self) -> None:
        spec = get_foundation("rf-detr-nano")
        assert spec is not None
        assert spec.task == "detection"

    def test_it_renders_as_boxes_not_by_task_name(self) -> None:
        """`render_hint` is what the overlay registry dispatches on — doc 20's rule."""
        spec = get_foundation("rf-detr-nano")
        assert spec is not None
        assert spec.render_hint == "boxes"

    def test_every_detector_names_an_apache_licensed_catalogue_entry(self) -> None:
        # The whole reason RF-DETR was chosen over the YOLO routes. If a future detector
        # arrives under a copyleft licence this fails rather than shipping quietly.
        for spec in all_foundations():
            if spec.task != "detection":
                continue
            model = get_model(spec.model_id)
            assert model is not None, spec.id
            assert model.licence == "Apache-2.0", spec.id
            assert model.non_commercial is False, spec.id

    def test_build_returns_a_detector_for_a_detection_spec(self) -> None:
        assert isinstance(build_foundation("rf-detr-nano"), RfDetrModel)

    def test_depth_and_detection_get_different_implementations(self) -> None:
        detector = build_foundation("rf-detr-nano")
        depth = build_foundation("depth-anything-v2-small")
        assert type(detector) is not type(depth)


class TestCoordinateConversion:
    def test_corners_become_width_and_height(self) -> None:
        results = {
            "boxes": torch.tensor([[10.0, 20.0, 50.0, 80.0]]),
            "scores": torch.tensor([0.9]),
            "labels": torch.tensor([3]),
        }
        boxes, scores, classes = _as_xywh(results)

        # xyxy (10,20)-(50,80) is xywh (10,20,40,60). Reading it as a size would give
        # a box of 50x80 at (10,20) — plausible-looking and wrong.
        assert boxes == [(10.0, 20.0, 40.0, 60.0)]
        assert scores == pytest.approx([0.9])
        assert classes == [3]

    def test_it_keeps_the_three_arrays_the_same_length(self) -> None:
        results = {
            "boxes": torch.tensor([[0.0, 0.0, 4.0, 4.0], [1.0, 1.0, 5.0, 6.0]]),
            "scores": torch.tensor([0.8, 0.7]),
            "labels": torch.tensor([1, 2]),
        }
        boxes, scores, classes = _as_xywh(results)
        assert len(boxes) == len(scores) == len(classes) == 2

    def test_it_accepts_tensors_that_are_not_plain_cpu_leaves(self) -> None:
        """Wave 3's bug: `.numpy()`/`.tolist()` behave differently on a tensor with a
        device or a graph, and every unit test builds plain CPU tensors."""
        results = {
            "boxes": torch.tensor([[0.0, 0.0, 4.0, 4.0]], requires_grad=True),
            "scores": torch.tensor([0.8], requires_grad=True),
            "labels": torch.tensor([1]),
        }
        boxes, _, _ = _as_xywh(results)
        assert boxes == [(0.0, 0.0, 4.0, 4.0)]

    def test_an_empty_result_is_not_an_error(self) -> None:
        # An image with nothing in it is ordinary input, not a failure.
        results = {
            "boxes": torch.zeros((0, 4)),
            "scores": torch.zeros((0,)),
            "labels": torch.zeros((0,), dtype=torch.long),
        }
        assert _as_xywh(results) == ([], [], [])


class TestThePayloadIsIndistinguishableFromAHeads:
    def test_it_carries_the_keys_the_renderer_reads(self) -> None:
        payload = source_boxes_payload([(1.0, 2.0, 3.0, 4.0)], [0.9], [0])
        assert set(payload) == {"boxes", "scores", "classes"}

    def test_a_zero_area_box_is_dropped_from_all_three_arrays(self) -> None:
        # Dropping it from `boxes` alone would shift every later score onto the wrong box.
        payload = source_boxes_payload(
            [(0.0, 0.0, 0.0, 5.0), (1.0, 1.0, 4.0, 4.0)], [0.9, 0.5], [7, 8]
        )
        assert payload["boxes"] == [[1.0, 1.0, 4.0, 4.0]]
        assert payload["scores"] == [0.5]
        assert payload["classes"] == [8]

    def test_it_caps_the_number_of_detections(self) -> None:
        count = MAX_DISPLAY_BOXES + 20
        payload = source_boxes_payload(
            [(0.0, 0.0, 2.0, 2.0)] * count, [0.5] * count, [0] * count
        )
        assert len(payload["boxes"]) == MAX_DISPLAY_BOXES  # type: ignore[arg-type]

    def test_prediction_reads_it_back_as_aligned_detections(self) -> None:
        """`Prediction.detections` returns nothing at all if the arrays disagree, so this
        is what proves the payload was assembled by the sanctioned path."""
        payload = source_boxes_payload([(1.0, 2.0, 3.0, 4.0)], [0.9], [1])
        prediction = Prediction(
            instance_id="rf-detr-nano",
            head_name="RF-DETR (nano)",
            head_type_id="rf-detr-nano",
            task="detection",
            render_hint="boxes",
            class_names=("background", "person"),
            payload=payload,
        )

        assert prediction.detections() == [((1.0, 2.0, 3.0, 4.0), 0.9, "person")]
        assert prediction.summary == "1 object"

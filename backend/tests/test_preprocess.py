"""Tests for task-aware preprocessing and target alignment.

The load-bearing test is `test_letterbox_never_drops_a_box`: dense tasks letterbox
precisely so no annotation can leave the frame. If that regresses, detection trains on
images whose ground truth has silently vanished while the loss still looks healthy —
which is exactly the failure doc 07 flagged.
"""

from __future__ import annotations

import random

import numpy
import pytest
import torch
from PIL import Image

from app.ml.backbone import BackboneCapabilities
from app.ml.heads.registry import get_head_type
from app.ml.preprocess import (
    GeometryTransform,
    apply_geometry,
    plan_preprocessing,
    to_pixel_values,
    transform_boxes,
    transform_mask,
)


def capabilities(patch_size: int = 14, embed_dim: int = 384) -> BackboneCapabilities:
    return BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=patch_size,
        embed_dim=embed_dim,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )


def spec_for(head_id: str):  # type: ignore[no-untyped-def]
    found = get_head_type(head_id)
    assert found is not None
    return found


class TestPlanPreprocessing:
    def test_classification_uses_center_crop(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("linear-classifier"))
        assert plan.geometry == "center-crop"

    def test_dense_tasks_preserve_aspect(self) -> None:
        for head_id in ("dense-detector", "linear-segmenter", "linear-depth"):
            plan = plan_preprocessing(capabilities(), spec_for(head_id))
            assert plan.geometry == "aspect-preserve", head_id

    def test_size_is_divisible_by_patch_size(self) -> None:
        """Doc 07 rejects indivisible inputs; a bad size must fail here, not at forward."""
        for patch_size in (14, 16):
            for head_id in ("linear-classifier", "dense-detector"):
                plan = plan_preprocessing(capabilities(patch_size=patch_size), spec_for(head_id))
                assert plan.size % patch_size == 0

    def test_dense_tasks_get_a_finer_grid_than_classification(self) -> None:
        """A 16x16 grid cannot express small objects."""
        cls_plan = plan_preprocessing(capabilities(), spec_for("linear-classifier"))
        det_plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        assert det_plan.size > cls_plan.size

    def test_normalisation_falls_back_to_imagenet(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("linear-classifier"))
        assert plan.mean == pytest.approx((0.485, 0.456, 0.406))
        assert plan.std == pytest.approx((0.229, 0.224, 0.225))


class TestApplyGeometryLetterbox:
    def test_output_is_square_and_planned_size(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        image, _ = apply_geometry(plan, Image.new("RGB", (640, 480)))
        assert image.size == (plan.size, plan.size)

    def test_scale_fits_the_longest_edge(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        _, transform = apply_geometry(plan, Image.new("RGB", (800, 400)))
        assert transform.scale == pytest.approx(plan.size / 800)

    def test_padding_is_centred(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        _, transform = apply_geometry(plan, Image.new("RGB", (800, 400)))
        assert transform.pad_x == pytest.approx(0.0)
        assert transform.pad_y > 0

    def test_square_input_needs_no_padding(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        _, transform = apply_geometry(plan, Image.new("RGB", (500, 500)))
        assert transform.pad_x == pytest.approx(0.0)
        assert transform.pad_y == pytest.approx(0.0)


class TestTransformBoxes:
    def test_box_follows_the_image(self) -> None:
        """A box covering the whole source must cover the whole scaled content."""
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        _, transform = apply_geometry(plan, Image.new("RGB", (800, 400)))
        boxes, keep = transform_boxes(transform, [(0.0, 0.0, 800.0, 400.0)])
        assert keep == [0]
        x, y, w, h = boxes[0]
        assert x == pytest.approx(0.0)
        assert y == pytest.approx(transform.pad_y)
        assert w == pytest.approx(plan.size)

    def test_letterbox_never_drops_a_box(self) -> None:
        """The reason dense tasks letterbox: no annotation can leave the frame."""
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        rng = random.Random(1234)
        for _ in range(200):
            width = rng.randint(32, 2000)
            height = rng.randint(32, 2000)
            _, transform = apply_geometry(plan, Image.new("RGB", (width, height)))
            boxes = [
                (
                    float(x := rng.randint(0, width - 8)),
                    float(y := rng.randint(0, height - 8)),
                    float(rng.randint(4, width - int(x))),
                    float(rng.randint(4, height - int(y))),
                )
                for _ in range(5)
            ]
            _, keep = transform_boxes(transform, boxes)
            assert keep == [0, 1, 2, 3, 4], (width, height)

    def test_transformed_boxes_stay_inside_the_canvas(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        _, transform = apply_geometry(plan, Image.new("RGB", (1000, 250)))
        boxes, _ = transform_boxes(transform, [(0.0, 0.0, 1000.0, 250.0)])
        x, y, w, h = boxes[0]
        assert x >= -1e-6 and y >= -1e-6
        assert x + w <= plan.size + 1e-6
        assert y + h <= plan.size + 1e-6

    def test_centre_crop_can_drop_and_reports_which(self) -> None:
        """Alignment is the point: a dropped box must drop its label with it."""
        plan = plan_preprocessing(capabilities(), spec_for("linear-classifier"))
        _, transform = apply_geometry(plan, Image.new("RGB", (2000, 200)))
        # Far-left box lies outside the centre crop; the centred one survives.
        boxes, keep = transform_boxes(
            transform, [(0.0, 0.0, 10.0, 10.0), (990.0, 90.0, 20.0, 20.0)]
        )
        assert 1 in keep
        assert len(boxes) == len(keep)

    def test_degenerate_box_is_dropped_not_clamped(self) -> None:
        """Zero-area boxes fail the store's CHECK and mean nothing to a loss."""
        plan = plan_preprocessing(capabilities(), spec_for("linear-classifier"))
        _, transform = apply_geometry(plan, Image.new("RGB", (2000, 200)))
        boxes, keep = transform_boxes(transform, [(0.0, 0.0, 1.0, 1.0)])
        assert all(w > 0 and h > 0 for _, _, w, h in boxes)
        assert len(boxes) == len(keep)

    def test_empty_input_yields_empty_output(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        _, transform = apply_geometry(plan, Image.new("RGB", (100, 100)))
        assert transform_boxes(transform, []) == ([], [])


class TestTransformMask:
    def test_mask_matches_the_planned_size(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("linear-segmenter"))
        mask = Image.new("L", (640, 480), 3)
        assert transform_mask(plan, mask).size == (plan.size, plan.size)

    def test_class_ids_are_preserved(self) -> None:
        """Bilinear resampling would invent class ids that were never annotated."""
        plan = plan_preprocessing(capabilities(), spec_for("linear-segmenter"))
        mask = Image.new("L", (100, 100), 0)
        for x in range(40, 60):
            for y in range(40, 60):
                mask.putpixel((x, y), 7)
        out = transform_mask(plan, mask)
        assert set(numpy.asarray(out).flatten().tolist()) <= {0, 7}

    def test_padding_uses_the_ignore_index(self) -> None:
        """Padded regions are not class 0 — they are not annotated at all."""
        plan = plan_preprocessing(capabilities(), spec_for("linear-segmenter"))
        out = transform_mask(plan, Image.new("L", (400, 100), 5), ignore_index=255)
        assert 255 in set(numpy.asarray(out).flatten().tolist())


class TestToPixelValues:
    def test_shape_and_dtype(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        image, _ = apply_geometry(plan, Image.new("RGB", (640, 480)))
        tensor = to_pixel_values(plan, [image])
        assert tensor.shape == (1, 3, plan.size, plan.size)
        assert tensor.dtype == torch.float32

    def test_batches_multiple_images(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        images = [apply_geometry(plan, Image.new("RGB", (100, 200)))[0] for _ in range(3)]
        assert to_pixel_values(plan, images).shape[0] == 3

    def test_normalisation_is_applied(self) -> None:
        """A mid-grey image must not come out as raw 0.5 if mean/std were applied."""
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        image = Image.new("RGB", (plan.size, plan.size), (128, 128, 128))
        tensor = to_pixel_values(plan, [image])
        assert not torch.allclose(tensor, torch.full_like(tensor, 128 / 255))

    def test_grayscale_input_is_converted_to_rgb(self) -> None:
        plan = plan_preprocessing(capabilities(), spec_for("dense-detector"))
        image, _ = apply_geometry(plan, Image.new("L", (64, 64), 120))
        assert to_pixel_values(plan, [image]).shape[1] == 3


class TestGeometryTransformIdentity:
    def test_identity_transform_leaves_boxes_untouched(self) -> None:
        transform = GeometryTransform(
            scale=1.0, pad_x=0.0, pad_y=0.0, out_w=100, out_h=100, source_size=(100, 100)
        )
        boxes, keep = transform_boxes(transform, [(10.0, 20.0, 30.0, 40.0)])
        assert boxes[0] == pytest.approx((10.0, 20.0, 30.0, 40.0))
        assert keep == [0]

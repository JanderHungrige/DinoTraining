"""Tests for putting predictions back into the original image's coordinates.

Every assertion here is a round trip: push a known box through the *forward* transform
the trainer uses, then invert it, and require the original back. That is the only check
that actually proves the inverse — an inverse that is subtly wrong still produces
plausible numbers, and a box drawn 12 pixels off looks like a bad model rather than a
bad transform.
"""

from __future__ import annotations

import pytest
import torch
from PIL import Image

from app.ml.backbone import BackboneCapabilities
from app.ml.heads.registry import get_head_type
from app.ml.inference.geometry import invert_boxes, invert_map
from app.ml.preprocess import (
    apply_geometry,
    plan_preprocessing,
    transform_boxes,
)


def capabilities(patch_size: int = 14) -> BackboneCapabilities:
    return BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=patch_size,
        embed_dim=384,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )


def spec_for(head_id: str):  # type: ignore[no-untyped-def]
    found = get_head_type(head_id)
    assert found is not None
    return found


def plan_for(head_id: str):  # type: ignore[no-untyped-def]
    return plan_preprocessing(capabilities(), spec_for(head_id))


# Dense tasks letterbox; classification centre-crops. Both must invert.
DENSE = "dense-detector"
CLASSIFY = "linear-classifier"


class TestInvertBoxesRoundTrip:
    @pytest.mark.parametrize("size", [(800, 400), (400, 800), (500, 500), (200, 900)])
    def test_letterbox_round_trip(self, size: tuple[int, int]) -> None:
        plan = plan_for(DENSE)
        image = Image.new("RGB", size)
        _, transform = apply_geometry(plan, image)

        original = [(50.0, 60.0, 120.0, 80.0)]
        moved, keep = transform_boxes(transform, original)
        assert keep == [0], "box should survive a letterbox — nothing leaves the frame"

        recovered = invert_boxes(transform, moved)
        for got, want in zip(recovered[0], original[0], strict=True):
            assert got == pytest.approx(want, abs=1.0)

    def test_centre_crop_round_trip_for_a_box_inside_the_crop(self) -> None:
        """Centre-crop discards content, so only a box inside the crop can round trip."""
        plan = plan_for(CLASSIFY)
        image = Image.new("RGB", (600, 600))
        _, transform = apply_geometry(plan, image)

        original = [(280.0, 280.0, 40.0, 40.0)]  # dead centre
        moved, keep = transform_boxes(transform, original)
        assert keep == [0]

        recovered = invert_boxes(transform, moved)
        for got, want in zip(recovered[0], original[0], strict=True):
            assert got == pytest.approx(want, abs=2.0)

    def test_a_box_at_the_far_edge_of_a_panorama_survives(self) -> None:
        """The 200x900 case from doc 07: letterbox must not lose the far edge."""
        plan = plan_for(DENSE)
        image = Image.new("RGB", (900, 200))
        _, transform = apply_geometry(plan, image)

        original = [(850.0, 80.0, 40.0, 40.0)]
        moved, keep = transform_boxes(transform, original)
        assert keep == [0]

        recovered = invert_boxes(transform, moved)
        assert recovered[0][0] == pytest.approx(850.0, abs=2.0)

    def test_empty_input(self) -> None:
        plan = plan_for(DENSE)
        _, transform = apply_geometry(plan, Image.new("RGB", (400, 300)))
        assert invert_boxes(transform, []) == []

    def test_output_is_clipped_to_the_source_image(self) -> None:
        """A detector can predict into the padding; those pixels do not exist."""
        plan = plan_for(DENSE)
        _, transform = apply_geometry(plan, Image.new("RGB", (400, 200)))

        # A box covering the whole padded canvas, including the grey bars.
        recovered = invert_boxes(transform, [(0.0, 0.0, float(plan.size), float(plan.size))])
        x, y, w, h = recovered[0]
        assert x >= 0 and y >= 0
        assert x + w <= 400 + 1
        assert y + h <= 200 + 1

    def test_scale_is_applied_to_extent_not_just_origin(self) -> None:
        """Forgetting to divide w/h by scale is the classic half-right inversion."""
        plan = plan_for(DENSE)
        _, transform = apply_geometry(plan, Image.new("RGB", (900, 300)))

        moved, _ = transform_boxes(transform, [(100.0, 100.0, 200.0, 100.0)])
        recovered = invert_boxes(transform, moved)
        assert recovered[0][2] == pytest.approx(200.0, abs=2.0)
        assert recovered[0][3] == pytest.approx(100.0, abs=2.0)


class TestInvertMap:
    def test_letterbox_map_returns_source_resolution(self) -> None:
        plan = plan_for(DENSE)
        _, transform = apply_geometry(plan, Image.new("RGB", (800, 400)))

        frame = torch.zeros(plan.size, plan.size)
        out = invert_map(transform, frame, mode="nearest")
        assert out.shape == (400, 800)

    def test_padding_is_stripped_before_rescaling(self) -> None:
        """The grey bars are not part of the image and must not appear in the output.

        The frame is marked 1 inside the pasted content and 9 in the padding; nothing
        valued 9 may survive the inversion.
        """
        plan = plan_for(DENSE)
        source = (900, 300)
        _, transform = apply_geometry(plan, Image.new("RGB", source))

        frame = torch.full((plan.size, plan.size), 9.0)
        content_w = round(source[0] * transform.scale)
        content_h = round(source[1] * transform.scale)
        top, left = int(transform.pad_y), int(transform.pad_x)
        frame[top : top + content_h, left : left + content_w] = 1.0

        out = invert_map(transform, frame, mode="nearest")
        assert out.shape == (300, 900)
        assert torch.all(out == 1.0), "padding leaked into the inverted map"

    def test_nearest_mode_invents_no_class_ids(self) -> None:
        """Bilinear on a label map averages class ids into classes nobody annotated."""
        plan = plan_for(DENSE)
        _, transform = apply_geometry(plan, Image.new("RGB", (600, 400)))

        frame = torch.zeros(plan.size, plan.size)
        frame[:, : plan.size // 2] = 3.0
        frame[:, plan.size // 2 :] = 7.0

        out = invert_map(transform, frame, mode="nearest")
        assert set(out.unique().tolist()) <= {3.0, 7.0}

    def test_bilinear_mode_is_available_for_depth(self) -> None:
        plan = plan_for(DENSE)
        _, transform = apply_geometry(plan, Image.new("RGB", (500, 250)))

        frame = torch.rand(plan.size, plan.size) * 10
        out = invert_map(transform, frame, mode="bilinear")
        assert out.shape == (250, 500)
        assert torch.isfinite(out).all()


class TestFullyOutOfFrame:
    def test_a_box_entirely_in_the_padding_collapses_inside_the_source(self) -> None:
        """Regression: clamping only at zero left the origin outside the image.

        A detector predicts on the whole padded canvas, so a cell in the grey bars is
        a normal occurrence. Its inverse must still be a point on the source image —
        zero-area is fine, y=361 on a 300px image is not.
        """
        plan = plan_for(DENSE)
        source = (900, 300)
        _, transform = apply_geometry(plan, Image.new("RGB", source))

        # A small box near the bottom of the canvas, well inside the padding.
        recovered = invert_boxes(transform, [(10.0, float(plan.size) - 5.0, 20.0, 4.0)])
        x, y, w, h = recovered[0]
        assert 0 <= x <= source[0]
        assert 0 <= y <= source[1]
        assert w >= 0 and h >= 0

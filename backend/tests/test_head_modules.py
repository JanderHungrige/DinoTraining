"""Tests for the four head modules.

The uniform call signature is what keeps the trainer generic, so it is asserted for
every head rather than per-head. The ltrb decode gets the same scrutiny Wave 1 gave
the detector's xyxy→xywh conversion — it is the one place that conversion happens.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.backbone import BackboneFeatures
from app.ml.heads.modules import (
    DETECTION_UPSAMPLE,
    ClassificationHead,
    DepthHead,
    DetectionHead,
    SegmentationHead,
    decode_ltrb_to_boxes,
    upsample_logits,
)

EMBED_DIM = 32
GRID = (4, 6)


def features(batch: int = 2, embed_dim: int = EMBED_DIM) -> BackboneFeatures:
    rows, cols = GRID
    return BackboneFeatures(
        cls=torch.randn(batch, embed_dim),
        patches=torch.randn(batch, embed_dim, rows, cols),
        grid=GRID,
    )


class TestClassificationHead:
    def test_output_shape(self) -> None:
        head = ClassificationHead(embed_dim=EMBED_DIM, num_classes=5)
        out = head(features(batch=3))
        assert out["logits"].shape == (3, 5)

    def test_consumes_the_cls_token_only(self) -> None:
        """Corrupting the patch grid must not change a classification prediction."""
        head = ClassificationHead(embed_dim=EMBED_DIM, num_classes=4).eval()
        feats = features(batch=1)
        baseline = head(feats)["logits"]
        poisoned = BackboneFeatures(
            cls=feats.cls, patches=torch.randn_like(feats.patches), grid=feats.grid
        )
        assert torch.allclose(baseline, head(poisoned)["logits"])

    def test_parameters_are_trainable(self) -> None:
        head = ClassificationHead(embed_dim=EMBED_DIM, num_classes=2)
        assert all(p.requires_grad for p in head.parameters())
        assert any(True for _ in head.parameters())


class TestDetectionHead:
    def test_it_predicts_at_twice_the_patch_grid(self) -> None:
        """Doc 43: the detector's grid is finer than the backbone's, which is the whole
        point — a 14 px cell cannot place a 35 px object to within 75% IoU."""
        head = DetectionHead(embed_dim=EMBED_DIM, num_classes=3)
        out = head(features(batch=2))
        rows, cols = GRID[0] * DETECTION_UPSAMPLE, GRID[1] * DETECTION_UPSAMPLE
        assert out["class_logits"].shape == (2, 3, rows, cols)
        assert out["box_ltrb"].shape == (2, 4, rows, cols)
        assert out["centerness"].shape == (2, 1, rows, cols)

    def test_its_stride_is_half_the_patch_size(self) -> None:
        # `box_ltrb` is scaled by this, and the assigner and decoder must agree with it.
        head = DetectionHead(embed_dim=EMBED_DIM, num_classes=3, patch_size=14)
        assert head.stride == 7.0

    def test_box_distances_are_positive(self) -> None:
        """A raw linear output would allow negative extents and inverted boxes."""
        head = DetectionHead(embed_dim=EMBED_DIM, num_classes=3)
        out = head(features(batch=4))
        assert bool((out["box_ltrb"] > 0).all())

    def test_consumes_the_patch_grid(self) -> None:
        head = DetectionHead(embed_dim=EMBED_DIM, num_classes=2).eval()
        feats = features(batch=1)
        baseline = head(feats)["class_logits"]
        changed = BackboneFeatures(
            cls=feats.cls, patches=torch.randn_like(feats.patches), grid=feats.grid
        )
        assert not torch.allclose(baseline, head(changed)["class_logits"])

    def test_parameters_are_trainable(self) -> None:
        head = DetectionHead(embed_dim=EMBED_DIM, num_classes=2)
        assert all(p.requires_grad for p in head.parameters())


class TestSegmentationHead:
    def test_output_shape_is_patch_resolution(self) -> None:
        """Upsampling needs a target size the head does not know — that is deliberate."""
        head = SegmentationHead(embed_dim=EMBED_DIM, num_classes=7)
        rows, cols = GRID
        assert head(features(batch=2))["logits"].shape == (2, 7, rows, cols)

    def test_parameters_are_trainable(self) -> None:
        head = SegmentationHead(embed_dim=EMBED_DIM, num_classes=3)
        assert all(p.requires_grad for p in head.parameters())


class TestDepthHead:
    def test_single_channel_output(self) -> None:
        head = DepthHead(embed_dim=EMBED_DIM)
        rows, cols = GRID
        assert head(features(batch=2))["depth"].shape == (2, 1, rows, cols)

    def test_builds_despite_not_being_trainable_in_app(self) -> None:
        """'Not trainable' means this app cannot fine-tune it, not that it cannot exist."""
        assert any(True for _ in DepthHead(embed_dim=EMBED_DIM).parameters())


class TestUniformContract:
    """Every head takes BackboneFeatures and returns dict[str, Tensor]."""

    def test_all_heads_share_the_call_signature(self) -> None:
        heads = [
            ClassificationHead(embed_dim=EMBED_DIM, num_classes=3),
            DetectionHead(embed_dim=EMBED_DIM, num_classes=3),
            SegmentationHead(embed_dim=EMBED_DIM, num_classes=3),
            DepthHead(embed_dim=EMBED_DIM),
        ]
        for head in heads:
            out = head(features())
            assert isinstance(out, dict)
            assert out
            assert all(isinstance(key, str) for key in out)
            assert all(isinstance(value, torch.Tensor) for value in out.values())

    def test_gradients_flow_to_head_parameters(self) -> None:
        head = ClassificationHead(embed_dim=EMBED_DIM, num_classes=3)
        head(features(batch=2))["logits"].sum().backward()
        assert all(p.grad is not None for p in head.parameters())


class TestUpsampleLogits:
    def test_upsamples_to_the_requested_size(self) -> None:
        logits = torch.randn(2, 5, 4, 6)
        assert upsample_logits(logits, (64, 96)).shape == (2, 5, 64, 96)

    def test_preserves_batch_and_channels(self) -> None:
        logits = torch.randn(3, 7, 4, 6)
        out = upsample_logits(logits, (32, 32))
        assert out.shape[0] == 3
        assert out.shape[1] == 7


class TestDecodeLtrbToBoxes:
    def test_centre_cell_decodes_to_expected_box(self) -> None:
        """One cell, distances 10 each way, patch 10 → centre (5,5), box (-5,-5,15,15)."""
        ltrb = torch.zeros(1, 4, 1, 1)
        ltrb[0, :, 0, 0] = 10.0
        boxes = decode_ltrb_to_boxes(ltrb, grid=(1, 1), patch_size=10)
        x, y, w, h = boxes[0, 0].tolist()
        assert (x, y) == pytest.approx((-5.0, -5.0))
        assert (w, h) == pytest.approx((20.0, 20.0))

    def test_output_shape_is_cells_by_four(self) -> None:
        ltrb = torch.rand(2, 4, 3, 5) + 1.0
        assert decode_ltrb_to_boxes(ltrb, grid=(3, 5), patch_size=14).shape == (2, 15, 4)

    def test_widths_and_heights_are_positive(self) -> None:
        ltrb = torch.rand(1, 4, 4, 4) + 0.5
        boxes = decode_ltrb_to_boxes(ltrb, grid=(4, 4), patch_size=14)
        assert bool((boxes[..., 2] > 0).all())
        assert bool((boxes[..., 3] > 0).all())

    def test_asymmetric_distances_shift_the_box(self) -> None:
        """left=0 right=20 must put the cell centre at the box's left edge."""
        ltrb = torch.zeros(1, 4, 1, 1)
        ltrb[0, 0, 0, 0] = 0.0   # left
        ltrb[0, 1, 0, 0] = 0.0   # top
        ltrb[0, 2, 0, 0] = 20.0  # right
        ltrb[0, 3, 0, 0] = 20.0  # bottom
        x, y, w, h = decode_ltrb_to_boxes(ltrb, grid=(1, 1), patch_size=10)[0, 0].tolist()
        assert (x, y) == pytest.approx((5.0, 5.0))
        assert (w, h) == pytest.approx((20.0, 20.0))

"""Tests for the pretrained default head modules.

The concat-order tests are the point of this file. The classification and depth heads
both take a ``2 * embed_dim`` input but assemble it in **opposite** orders, and getting
one wrong produces a correctly-shaped tensor full of wrong numbers — the failure mode
no shape assertion can catch.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.backbone import BackboneCapabilities, BackboneFeatures
from app.ml.heads.pretrained import (
    ADE20K_CLASSES,
    IMAGENET_CLASSES,
    NYU_DEPTH_RANGE,
    PretrainedClassifier,
    PretrainedDepth,
    PretrainedSegmenter,
)

EMBED = 8
BATCH = 2
GRID = (3, 4)


def capabilities(embed_dim: int = EMBED) -> BackboneCapabilities:
    return BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=14,
        embed_dim=embed_dim,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )


def features(embed_dim: int = EMBED, cls_fill: float = 1.0, patch_fill: float = 1.0):
    rows, cols = GRID
    return BackboneFeatures(
        cls=torch.full((BATCH, embed_dim), cls_fill),
        patches=torch.full((BATCH, embed_dim, rows, cols), patch_fill),
        grid=GRID,
    )


class TestClassifier:
    def test_output_shape_and_key(self) -> None:
        head = PretrainedClassifier(embed_dim=EMBED)
        out = head(features())
        assert set(out) == {"logits"}
        assert out["logits"].shape == (BATCH, IMAGENET_CLASSES)

    def test_input_width_is_twice_embed_dim(self) -> None:
        """cat([cls, mean(patches)]) — the upstream checkpoint is (1000, 2*D)."""
        head = PretrainedClassifier(embed_dim=EMBED)
        assert head.linear.weight.shape == (IMAGENET_CLASSES, EMBED * 2)

    def test_cls_token_occupies_the_first_half(self) -> None:
        """CLS first, pooled patches second (dinov2/eval/linear.py create_linear_input).

        Zeroing the second half must make the head blind to the patch grid while
        remaining sensitive to CLS. If the halves were swapped this assertion flips.
        """
        head = PretrainedClassifier(embed_dim=EMBED, num_classes=1)
        with torch.no_grad():
            head.linear.weight.fill_(0.0)
            head.linear.bias.fill_(0.0)
            head.linear.weight[:, :EMBED] = 1.0  # listen to CLS only

        varying_patches = head(features(cls_fill=1.0, patch_fill=99.0))["logits"]
        baseline = head(features(cls_fill=1.0, patch_fill=0.0))["logits"]
        assert torch.allclose(varying_patches, baseline)
        assert torch.allclose(baseline, torch.full((BATCH, 1), float(EMBED)))

    def test_patches_are_average_pooled_not_flattened(self) -> None:
        head = PretrainedClassifier(embed_dim=EMBED, num_classes=1)
        with torch.no_grad():
            head.linear.weight.fill_(0.0)
            head.linear.bias.fill_(0.0)
            head.linear.weight[:, EMBED:] = 1.0  # listen to the pooled patches only

        # Mean over the grid of a constant 3.0 is 3.0, regardless of grid size.
        out = head(features(cls_fill=99.0, patch_fill=3.0))["logits"]
        assert torch.allclose(out, torch.full((BATCH, 1), 3.0 * EMBED))


class TestSegmenter:
    def test_output_shape_is_patch_resolution(self) -> None:
        head = PretrainedSegmenter(embed_dim=EMBED)
        head.eval()
        out = head(features())
        rows, cols = GRID
        assert out["logits"].shape == (BATCH, ADE20K_CLASSES, rows, cols)

    def test_input_width_is_embed_dim_with_no_cls_concat(self) -> None:
        """in_channels == channels == D upstream: the segmenter concatenates nothing."""
        head = PretrainedSegmenter(embed_dim=EMBED)
        assert head.conv_seg.weight.shape == (ADE20K_CLASSES, EMBED, 1, 1)
        assert head.bn.weight.shape == (EMBED,)

    def test_ignores_the_cls_token(self) -> None:
        head = PretrainedSegmenter(embed_dim=EMBED)
        head.eval()
        first = head(features(cls_fill=0.0))["logits"]
        second = head(features(cls_fill=50.0))["logits"]
        assert torch.allclose(first, second)

    def test_batchnorm_runs_in_eval_mode_without_error(self) -> None:
        """Imported BN carries running stats; the head is never trained here."""
        head = PretrainedSegmenter(embed_dim=EMBED)
        head.eval()
        with torch.no_grad():
            out = head(features())
        assert torch.isfinite(out["logits"]).all()


class TestDepth:
    def test_output_shape_and_key(self) -> None:
        head = PretrainedDepth(embed_dim=EMBED)
        out = head(features())
        rows, cols = GRID
        assert set(out) == {"depth"}
        # Same key and shape as the built-in DepthHead, so renderers need no branch.
        assert out["depth"].shape == (BATCH, 1, rows, cols)

    def test_input_width_is_twice_embed_dim(self) -> None:
        head = PretrainedDepth(embed_dim=EMBED)
        assert head.conv_depth.weight.shape == (head.n_bins, EMBED * 2, 1, 1)

    def test_patches_occupy_the_first_half(self) -> None:
        """Opposite order to the classifier: cat([patches, cls]) in BNHead.

        Zeroing the *second* half must make the head blind to CLS. Together with
        test_cls_occupies_the_second_half this pins the ordering from both sides.
        """
        head = PretrainedDepth(embed_dim=EMBED)
        with torch.no_grad():
            head.conv_depth.weight.fill_(0.0)
            head.conv_depth.weight[:, :EMBED] = 1.0  # patch half only

        varying_cls = head(features(patch_fill=1.0, cls_fill=99.0))["depth"]
        baseline = head(features(patch_fill=1.0, cls_fill=0.0))["depth"]
        assert torch.allclose(varying_cls, baseline)

    def test_cls_occupies_the_second_half(self) -> None:
        head = PretrainedDepth(embed_dim=EMBED)
        with torch.no_grad():
            head.conv_depth.weight.fill_(0.0)
            head.conv_depth.weight[:, EMBED:] = 1.0  # cls half only

        varying_patches = head(features(cls_fill=1.0, patch_fill=99.0))["depth"]
        baseline = head(features(cls_fill=1.0, patch_fill=0.0))["depth"]
        assert torch.allclose(varying_patches, baseline)

    def test_depth_is_inside_the_declared_range(self) -> None:
        """Bin decoding is a convex combination, so output cannot escape the range."""
        minimum, maximum = NYU_DEPTH_RANGE
        head = PretrainedDepth(embed_dim=EMBED)
        with torch.no_grad():
            head.conv_depth.weight.normal_(0.0, 1.0)
            out = head(
                BackboneFeatures(
                    cls=torch.randn(BATCH, EMBED),
                    patches=torch.randn(BATCH, EMBED, *GRID),
                    grid=GRID,
                )
            )["depth"]
        assert (out >= minimum).all()
        assert (out <= maximum).all()

    def test_uniform_bin_weights_give_the_range_midpoint(self) -> None:
        """All-equal logits must decode to the mean of the bin centres, not to zero."""
        minimum, maximum = NYU_DEPTH_RANGE
        head = PretrainedDepth(embed_dim=EMBED)
        with torch.no_grad():
            head.conv_depth.weight.fill_(0.0)
            head.conv_depth.bias.fill_(0.0)
            out = head(features())["depth"]
        expected = (minimum + maximum) / 2
        assert torch.allclose(out, torch.full_like(out, expected), atol=1e-4)

    def test_range_comes_from_the_caller_not_a_constant(self) -> None:
        shallow = PretrainedDepth(embed_dim=EMBED, min_depth=0.0, max_depth=1.0)
        with torch.no_grad():
            shallow.conv_depth.weight.fill_(0.0)
            shallow.conv_depth.bias.fill_(0.0)
            out = shallow(features())["depth"]
        assert torch.allclose(out, torch.full_like(out, 0.5), atol=1e-4)


class TestStateDictContract:
    """Parameter names must be exactly what convert.py remaps upstream keys onto."""

    @pytest.mark.parametrize(
        ("head", "expected"),
        [
            (PretrainedClassifier(embed_dim=EMBED), {"linear.weight", "linear.bias"}),
            (
                PretrainedSegmenter(embed_dim=EMBED),
                {
                    "bn.weight",
                    "bn.bias",
                    "bn.running_mean",
                    "bn.running_var",
                    "bn.num_batches_tracked",
                    "conv_seg.weight",
                    "conv_seg.bias",
                },
            ),
            (
                PretrainedDepth(embed_dim=EMBED),
                {"conv_depth.weight", "conv_depth.bias"},
            ),
        ],
    )
    def test_state_dict_keys(self, head: torch.nn.Module, expected: set[str]) -> None:
        assert set(head.state_dict()) == expected

    def test_strict_load_round_trips(self) -> None:
        source = PretrainedSegmenter(embed_dim=EMBED)
        target = PretrainedSegmenter(embed_dim=EMBED)
        target.load_state_dict(source.state_dict(), strict=True)
        target.eval()
        source.eval()
        assert torch.allclose(source(features())["logits"], target(features())["logits"])

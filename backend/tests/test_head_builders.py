"""Tests for the head builder registry.

The sync test is the important one: a HeadTypeSpec with no builder fails the moment a
user selects it in the trainer, which is far too late to find out.
"""

from __future__ import annotations

import pytest
import torch

from app.ml.backbone import BackboneCapabilities, BackboneFeatures
from app.ml.heads.builders import HEAD_BUILDERS, build_head
from app.ml.heads.registry import all_head_types


def capabilities(embed_dim: int = 32) -> BackboneCapabilities:
    return BackboneCapabilities(
        model_id="dinov2-base",
        family="dinov2",
        patch_size=14,
        embed_dim=embed_dim,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )


def features(embed_dim: int = 32, batch: int = 2) -> BackboneFeatures:
    return BackboneFeatures(
        cls=torch.randn(batch, embed_dim),
        patches=torch.randn(batch, embed_dim, 4, 6),
        grid=(4, 6),
    )


class TestBuilderCoverage:
    def test_every_registry_spec_has_a_builder(self) -> None:
        """Adding a head type without a builder must not be discoverable only at runtime."""
        missing = [spec.id for spec in all_head_types() if spec.id not in HEAD_BUILDERS]
        assert missing == []

    def test_no_orphan_builders(self) -> None:
        known = {spec.id for spec in all_head_types()}
        assert [key for key in HEAD_BUILDERS if key not in known] == []


class TestBuildHead:
    def test_builds_every_trainable_head(self) -> None:
        for spec in all_head_types():
            if not spec.trainable:
                continue
            head = build_head(spec.id, capabilities(), num_classes=3)
            out = head(features())
            assert isinstance(out, dict) and out

    def test_builds_depth_without_classes(self) -> None:
        head = build_head("linear-depth", capabilities(), num_classes=None)
        assert head(features())["depth"].shape[1] == 1

    def test_width_follows_the_backbone(self) -> None:
        """Heads are sized from capabilities.embed_dim, never a constant."""
        head = build_head("linear-classifier", capabilities(embed_dim=128), num_classes=4)
        out = head(features(embed_dim=128))
        assert out["logits"].shape == (2, 4)

    def test_head_parameters_are_trainable(self) -> None:
        """The other half of the frozen-backbone pairing in doc 07."""
        head = build_head("dense-detector", capabilities(), num_classes=2)
        assert all(p.requires_grad for p in head.parameters())

    def test_unknown_head_type_raises_lookup_error(self) -> None:
        with pytest.raises(LookupError):
            build_head("not-a-head", capabilities(), num_classes=3)

    def test_trainable_head_requires_num_classes(self) -> None:
        with pytest.raises(ValueError, match="num_classes"):
            build_head("linear-classifier", capabilities(), num_classes=None)

    def test_num_classes_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match="num_classes"):
            build_head("linear-segmenter", capabilities(), num_classes=0)

    def test_depth_rejects_num_classes(self) -> None:
        """Passing classes to depth means the caller has confused two head types."""
        with pytest.raises(ValueError, match="num_classes"):
            build_head("linear-depth", capabilities(), num_classes=5)

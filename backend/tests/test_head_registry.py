"""Tests for the head-type contract.

The invariants matter more than the table: a trainable head with no best-model
criterion, or one selecting on a metric it never computes, both fail silently at
training time. They are enforced at construction and asserted here.
"""

from __future__ import annotations

import dataclasses

import pytest

from app.ml.backbone import BackboneCapabilities
from app.ml.heads.registry import (
    HEAD_TYPES,
    HeadTypeSpec,
    all_head_types,
    check_compatibility,
    get_head_type,
    head_types_for_task,
    trainable_head_types,
)


def capabilities(
    model_id: str = "dinov2-base",
    family: str = "dinov2",
    embed_dim: int = 768,
    patch_size: int = 14,
) -> BackboneCapabilities:
    return BackboneCapabilities(
        model_id=model_id,
        family=family,  # type: ignore[arg-type]
        patch_size=patch_size,
        embed_dim=embed_dim,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )


def spec(**overrides: object) -> HeadTypeSpec:
    """A valid trainable spec, so each invariant test breaks exactly one thing."""
    base: dict[str, object] = {
        "id": "test-head",
        "task": "classification",
        "title": "Test",
        "description": "A test head.",
        "trainable": True,
        "target_format": "image-labels",
        "consumes": "cls",
        "geometry": "center-crop",
        "metrics": ("accuracy", "macro_f1"),
        "primary_metric": "accuracy",
        "primary_metric_mode": "max",
        "render_hint": "labels",
        "compatible_families": frozenset({"dinov2", "dinov3"}),
    }
    base.update(overrides)
    return HeadTypeSpec(**base)  # type: ignore[arg-type]


class TestBuiltInTable:
    def test_every_task_has_a_head_type(self) -> None:
        tasks = {entry.task for entry in all_head_types()}
        assert tasks == {"classification", "detection", "segmentation", "depth"}

    def test_ids_are_unique(self) -> None:
        ids = [entry.id for entry in all_head_types()]
        assert len(ids) == len(set(ids))

    def test_keys_match_spec_ids(self) -> None:
        assert all(key == entry.id for key, entry in HEAD_TYPES.items())

    def test_depth_is_usable_but_not_trainable(self) -> None:
        """The deliberate proof that the registry does not assume a training loop."""
        depth = get_head_type("linear-depth")
        assert depth is not None
        assert depth.trainable is False
        assert depth.target_format is None
        assert depth.primary_metric is None

    def test_detection_and_segmentation_preserve_aspect(self) -> None:
        """Centre-cropping a dense task silently drops annotations — see doc 07."""
        for head_id in ("dense-detector", "linear-segmenter"):
            entry = get_head_type(head_id)
            assert entry is not None
            assert entry.geometry == "aspect-preserve"

    def test_classification_uses_the_cls_token(self) -> None:
        entry = get_head_type("linear-classifier")
        assert entry is not None
        assert entry.consumes == "cls"

    def test_dense_tasks_use_the_patch_grid(self) -> None:
        for head_id in ("dense-detector", "linear-segmenter", "linear-depth"):
            entry = get_head_type(head_id)
            assert entry is not None
            assert entry.consumes == "patch-grid"

    def test_render_hints_are_distinct_per_task(self) -> None:
        """Waves 3/4 dispatch drawing off this; two tasks sharing a hint would collide."""
        hints = {entry.task: entry.render_hint for entry in all_head_types()}
        assert hints["detection"] == "boxes"
        assert hints["segmentation"] == "masks"
        assert hints["depth"] == "depth-map"
        assert hints["classification"] == "labels"

    def test_specs_are_frozen(self) -> None:
        entry = get_head_type("linear-classifier")
        assert entry is not None
        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.id = "mutated"  # type: ignore[misc]


class TestLookup:
    def test_get_known_head_type(self) -> None:
        assert get_head_type("linear-classifier") is not None

    def test_unknown_head_type_returns_none(self) -> None:
        assert get_head_type("not-a-head") is None

    def test_filter_by_task(self) -> None:
        """Two segmentation heads since doc 15: the trainable one and the ADE20k default.

        This is what same-task comparison in Wave 3 lists — filtering by task is the
        whole mechanism, so more than one entry per task is the expected shape.
        """
        found = head_types_for_task("segmentation")
        assert [entry.id for entry in found] == [
            "linear-segmenter",
            "dinov2-linear-segmenter-ade20k",
        ]

    def test_filter_by_task_with_no_matches(self) -> None:
        assert head_types_for_task("pose") == ()  # type: ignore[arg-type]


class TestInvariants:
    def test_trainable_requires_a_target_format(self) -> None:
        with pytest.raises(ValueError, match="target_format"):
            spec(target_format=None)

    def test_trainable_requires_a_primary_metric(self) -> None:
        """Without one, save-best-only silently keeps the last epoch instead of the best."""
        with pytest.raises(ValueError, match="primary_metric"):
            spec(primary_metric=None, primary_metric_mode=None)

    def test_trainable_requires_a_metric_mode(self) -> None:
        with pytest.raises(ValueError, match="primary_metric_mode"):
            spec(primary_metric_mode=None)

    def test_trainable_requires_non_empty_metrics(self) -> None:
        with pytest.raises(ValueError, match="metrics"):
            spec(metrics=(), primary_metric="accuracy")

    def test_primary_metric_must_be_in_metrics(self) -> None:
        """Selecting on a metric that is never computed is a silent no-op."""
        with pytest.raises(ValueError, match="not in metrics|primary_metric"):
            spec(primary_metric="f2_score")

    def test_untrainable_must_not_have_a_target_format(self) -> None:
        with pytest.raises(ValueError, match="target_format"):
            spec(trainable=False, target_format="image-labels", primary_metric=None,
                 primary_metric_mode=None)

    def test_untrainable_must_not_have_a_primary_metric(self) -> None:
        with pytest.raises(ValueError, match="primary_metric"):
            spec(trainable=False, target_format=None)

    def test_valid_untrainable_spec_is_accepted(self) -> None:
        entry = spec(
            trainable=False, target_format=None, primary_metric=None, primary_metric_mode=None
        )
        assert entry.trainable is False

    def test_empty_compatible_families_rejected(self) -> None:
        """A head compatible with nothing is a configuration mistake, not a valid entry."""
        with pytest.raises(ValueError, match="compatible_families"):
            spec(compatible_families=frozenset())


class TestCompatibility:
    def test_supported_family_is_compatible(self) -> None:
        result = check_compatibility(spec(), capabilities(family="dinov2"))
        assert result.compatible is True
        assert result.reason is None

    def test_unsupported_family_is_explained(self) -> None:
        """The wave requires a reason, not a greyed-out row."""
        entry = spec(compatible_families=frozenset({"dinov3"}))
        result = check_compatibility(entry, capabilities(family="dinov2"))
        assert result.compatible is False
        assert result.reason is not None
        assert "dinov2" in result.reason
        assert "dinov3" in result.reason

    def test_every_trainable_head_supports_both_dino_families(self) -> None:
        """Heads this app builds from scratch fit any backbone width, so any family."""
        for entry in trainable_head_types():
            for family in ("dinov2", "dinov3"):
                assert check_compatibility(entry, capabilities(family=family)).compatible

    def test_pretrained_defaults_are_dinov2_only_and_say_so(self) -> None:
        """Doc 15: DINOv3 publishes no head this app can ship, and the user is told why.

        These carry actual DINOv2 weights, so unlike a from-scratch head they cannot
        adapt to another family — and per the wave rule the refusal must explain
        itself rather than grey the row out.
        """
        defaults = [entry for entry in all_head_types() if not entry.trainable]
        defaults = [entry for entry in defaults if entry.id.startswith("dinov2-")]
        assert len(defaults) == 3

        for entry in defaults:
            assert check_compatibility(entry, capabilities(family="dinov2")).compatible
            verdict = check_compatibility(entry, capabilities(family="dinov3"))
            assert verdict.compatible is False
            assert verdict.reason is not None
            assert "dinov3" in verdict.reason

    def test_embed_dim_is_not_a_type_level_constraint(self) -> None:
        """A linear head is built to whatever width the backbone reports."""
        small = check_compatibility(spec(), capabilities(embed_dim=384))
        large = check_compatibility(spec(), capabilities(embed_dim=1024))
        assert small.compatible and large.compatible

"""Tests for running N heads over one backbone pass per framing.

The claim this feature makes is not "N heads produce N predictions" — running them one
at a time does that too. It is that heads sharing a framing share a forward pass, and
that grouping the work does not reorder the answers. So the passes are counted, not
assumed.
"""

from __future__ import annotations

import pytest
import torch
from PIL import Image

from app.core.config import Settings
from app.ml.heads.registry import get_head_type
from app.ml.heads.store import HeadInstanceStore
from app.ml.inference.compose import pass_key, run_heads
from app.ml.inference.engine import BackboneMismatchError
from tests.head_testkit import install_fake_backbone

EMBED = 32

#: Every (height, width) `extract` was called with, in order. Cleared by the fixture.
EXTRACT_CALLS: list[tuple[int, int]] = []


class StubBackbone:
    def __init__(self, capabilities: object, device: str = "cpu") -> None:
        self.capabilities = capabilities
        self.device = device
        self.processor = None
        self.model = None


@pytest.fixture
def stubbed(monkeypatch: pytest.MonkeyPatch, head_settings: Settings) -> Settings:
    """Patch the backbone load + forward, and record every extract call."""
    from app.ml.backbone import BackboneCapabilities, BackboneFeatures

    EXTRACT_CALLS.clear()
    install_fake_backbone(head_settings, "dinov2-small", EMBED)
    capabilities = BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=14,
        embed_dim=EMBED,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )

    def fake_load(model_id: str = "dinov2-small") -> StubBackbone:
        return StubBackbone(capabilities)

    def fake_extract(backbone: object, pixel_values: torch.Tensor) -> BackboneFeatures:
        height, width = int(pixel_values.shape[-2]), int(pixel_values.shape[-1])
        EXTRACT_CALLS.append((height, width))
        rows, cols = height // 14, width // 14
        return BackboneFeatures(
            cls=torch.randn(1, EMBED),
            patches=torch.randn(1, EMBED, rows, cols),
            grid=(rows, cols),
        )

    monkeypatch.setattr("app.ml.inference.compose.load_backbone", fake_load)
    monkeypatch.setattr("app.ml.inference.compose.extract", fake_extract)
    return head_settings


def register(
    settings: Settings,
    head_type_id: str,
    num_classes: int,
    weights: dict[str, torch.Tensor],
    name: str = "",
    backbone_id: str = "dinov2-small",
) -> str:
    instance = HeadInstanceStore(settings).register(
        name=name or f"test {head_type_id}",
        kind="trained-here",
        head_type_id=head_type_id,
        task="",
        backbone_id=backbone_id,
        backbone_family="dinov2",
        embed_dim=EMBED,
        num_classes=num_classes,
        weights=weights,
        class_names=tuple(f"class{i}" for i in range(num_classes)),
    )
    return instance.id


def classifier_weights(num_classes: int) -> dict[str, torch.Tensor]:
    return {
        "linear.weight": torch.randn(num_classes, EMBED),
        "linear.bias": torch.randn(num_classes),
    }


def segmenter_weights(num_classes: int) -> dict[str, torch.Tensor]:
    return {
        "classifier.weight": torch.randn(num_classes, EMBED, 1, 1),
        "classifier.bias": torch.randn(num_classes),
    }


def detector_weights(num_classes: int) -> dict[str, torch.Tensor]:
    return {
        "classifier.weight": torch.randn(num_classes, EMBED, 1, 1),
        "classifier.bias": torch.randn(num_classes),
        "box_regressor.weight": torch.randn(4, EMBED, 1, 1),
        "box_regressor.bias": torch.randn(4),
        "centerness.weight": torch.randn(1, EMBED, 1, 1),
        "centerness.bias": torch.randn(1),
    }


IMAGE = Image.new("RGB", (900, 300))


class TestPassKey:
    """The key is `(backbone_id, geometry, size)` — and nothing else."""

    def test_the_key_is_only_backbone_geometry_and_size(self) -> None:
        from app.ml.backbone import BackboneCapabilities
        from app.ml.preprocess import plan_preprocessing

        capabilities = BackboneCapabilities(
            model_id="dinov2-small",
            family="dinov2",
            patch_size=14,
            embed_dim=EMBED,
            num_prefix_tokens=1,
            num_layers=12,
            image_size=518,
        )
        spec = get_head_type("linear-segmenter")
        assert spec is not None

        key = pass_key("dinov2-small", plan_preprocessing(capabilities, spec))

        assert key == ("dinov2-small", "aspect-preserve", 448)

    def test_consumes_does_not_reach_the_key(self) -> None:
        """`cls` and `patches` come out of the same BackboneFeatures.

        Every `cls` head in today's registry happens to be center-crop, so grouping
        alone cannot demonstrate this. Asserted at the key instead: the plan a head
        contributes to the key has no `consumes` field to leak into it.
        """
        from app.ml.preprocess import PreprocessPlan

        assert not hasattr(PreprocessPlan, "consumes")
        assert "consumes" not in PreprocessPlan.__annotations__


class TestPassSharing:
    def test_two_dense_heads_share_one_pass(self, stubbed: Settings) -> None:
        """Segmentation and detection are both aspect-preserve @ 448."""
        segmenter = register(stubbed, "linear-segmenter", 3, segmenter_weights(3))
        detector = register(stubbed, "dense-detector", 2, detector_weights(2))

        result = run_heads(IMAGE, "dinov2-small", [segmenter, detector], settings=stubbed)

        assert len(result.predictions) == 2
        assert result.passes == 1
        assert len(EXTRACT_CALLS) == 1

    def test_a_classifier_needs_its_own_pass(self, stubbed: Settings) -> None:
        """center-crop @ 224 cannot be sliced out of aspect-preserve @ 448."""
        classifier = register(stubbed, "linear-classifier", 3, classifier_weights(3))
        segmenter = register(stubbed, "linear-segmenter", 3, segmenter_weights(3))

        result = run_heads(IMAGE, "dinov2-small", [classifier, segmenter], settings=stubbed)

        assert result.passes == 2
        assert set(EXTRACT_CALLS) == {(224, 224), (448, 448)}

    def test_three_heads_two_framings_is_two_passes(self, stubbed: Settings) -> None:
        classifier = register(stubbed, "linear-classifier", 3, classifier_weights(3))
        segmenter = register(stubbed, "linear-segmenter", 3, segmenter_weights(3))
        detector = register(stubbed, "dense-detector", 2, detector_weights(2))

        result = run_heads(
            IMAGE, "dinov2-small", [classifier, segmenter, detector], settings=stubbed
        )

        assert len(result.predictions) == 3
        assert result.passes == 2
        assert len(EXTRACT_CALLS) == 2

    def test_one_head_is_one_pass(self, stubbed: Settings) -> None:
        classifier = register(stubbed, "linear-classifier", 3, classifier_weights(3))

        result = run_heads(IMAGE, "dinov2-small", [classifier], settings=stubbed)

        assert result.passes == 1
        assert len(result.predictions) == 1


class TestOrdering:
    def test_predictions_come_back_in_the_callers_order(self, stubbed: Settings) -> None:
        """Grouping reorders the work; it must not reorder the answers.

        The classifier is asked for first but runs in a different group from the two
        dense heads, so a naive group-then-concatenate moves it — and every column in a
        comparison view is then mislabelled.
        """
        classifier = register(stubbed, "linear-classifier", 3, classifier_weights(3), "A")
        segmenter = register(stubbed, "linear-segmenter", 3, segmenter_weights(3), "B")
        detector = register(stubbed, "dense-detector", 2, detector_weights(2), "C")

        result = run_heads(
            IMAGE, "dinov2-small", [segmenter, classifier, detector], settings=stubbed
        )

        assert [p.instance_id for p in result.predictions] == [segmenter, classifier, detector]
        assert [p.head_name for p in result.predictions] == ["B", "A", "C"]


class TestValidation:
    def test_an_empty_head_list_is_rejected(self, stubbed: Settings) -> None:
        with pytest.raises(ValueError):
            run_heads(IMAGE, "dinov2-small", [], settings=stubbed)

    def test_duplicates_are_collapsed_keeping_the_first(self, stubbed: Settings) -> None:
        classifier = register(stubbed, "linear-classifier", 3, classifier_weights(3))
        segmenter = register(stubbed, "linear-segmenter", 3, segmenter_weights(3))

        result = run_heads(
            IMAGE, "dinov2-small", [classifier, segmenter, classifier], settings=stubbed
        )

        assert [p.instance_id for p in result.predictions] == [classifier, segmenter]

    def test_an_unknown_head_fails_before_any_pass(self, stubbed: Settings) -> None:
        """Resolving lazily would charge the user a 448 pass to learn they mistyped."""
        segmenter = register(stubbed, "linear-segmenter", 3, segmenter_weights(3))

        with pytest.raises(LookupError):
            run_heads(IMAGE, "dinov2-small", [segmenter, "nope"], settings=stubbed)

        assert EXTRACT_CALLS == []

    def test_a_mismatched_backbone_fails_the_whole_request(self, stubbed: Settings) -> None:
        install_fake_backbone(stubbed, "dinov2-base", EMBED)
        good = register(stubbed, "linear-segmenter", 3, segmenter_weights(3))
        wrong = register(
            stubbed, "linear-classifier", 3, classifier_weights(3), backbone_id="dinov2-base"
        )

        with pytest.raises(BackboneMismatchError) as caught:
            run_heads(IMAGE, "dinov2-small", [good, wrong], settings=stubbed)

        # The message has to name the backbone that would work, or the user has no move.
        assert "dinov2-base" in str(caught.value)
        assert EXTRACT_CALLS == []


class TestTiming:
    def test_per_head_timings_exclude_the_shared_pass(self, stubbed: Settings) -> None:
        """The gap between the sum and the total *is* the saving. See doc 18."""
        segmenter = register(stubbed, "linear-segmenter", 3, segmenter_weights(3))
        detector = register(stubbed, "dense-detector", 2, detector_weights(2))

        result = run_heads(IMAGE, "dinov2-small", [segmenter, detector], settings=stubbed)

        per_head = sum(p.elapsed_ms for p in result.predictions)
        assert per_head <= result.elapsed_ms
        assert all(p.elapsed_ms >= 0 for p in result.predictions)


class TestSingleHeadPathStillWorks:
    def test_run_inference_delegates_rather_than_duplicating(self, stubbed: Settings) -> None:
        """Doc 16's entry point survives the refactor — one implementation, not two."""
        from app.ml.inference.engine import run_inference

        classifier = register(stubbed, "linear-classifier", 3, classifier_weights(3))
        prediction = run_inference(IMAGE, "dinov2-small", classifier, settings=stubbed)

        assert prediction.instance_id == classifier
        assert prediction.render_hint == "labels"
        # Patched on `compose`, not `engine` — proves the call went through the new path.
        assert len(EXTRACT_CALLS) == 1

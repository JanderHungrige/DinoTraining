"""Tests for composing a prediction from a frozen backbone and one head.

The ordering is what this feature actually contributes, so the tests care about it:
predictions must arrive in *source* coordinates, preprocessing must be derived rather
than accepted, and the decoder registry must be consulted rather than the task string.
"""

from __future__ import annotations

import pytest
import torch
from PIL import Image

from app.core.config import Settings
from app.ml.heads.store import HeadInstanceStore
from app.ml.inference.engine import BackboneMismatchError, run_inference
from tests.head_testkit import install_fake_backbone

EMBED = 32


class StubBackbone:
    """A backbone with the real shape contract and no weights.

    Loading dinov2-small would make every test in this file depend on a 168 MB download
    and several seconds of model load; the tensor contract from doc 07 is what the
    engine actually consumes, and it is fully expressible here.
    """

    def __init__(self, capabilities: object, device: str = "cpu") -> None:
        self.capabilities = capabilities
        self.device = device
        self.processor = None
        self.model = None


@pytest.fixture
def stubbed(monkeypatch: pytest.MonkeyPatch, head_settings: Settings):  # type: ignore[no-untyped-def]
    """Patch the backbone load + forward, leaving every other step real."""
    from app.ml.backbone import BackboneCapabilities, BackboneFeatures

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

    def fake_load(model_id: str = "dinov2-small"):  # type: ignore[no-untyped-def]
        return StubBackbone(capabilities)

    def fake_extract(backbone: object, pixel_values: torch.Tensor) -> BackboneFeatures:
        height, width = int(pixel_values.shape[-2]), int(pixel_values.shape[-1])
        rows, cols = height // 14, width // 14
        return BackboneFeatures(
            cls=torch.randn(1, EMBED),
            patches=torch.randn(1, EMBED, rows, cols),
            grid=(rows, cols),
        )

    monkeypatch.setattr("app.ml.inference.engine.load_backbone", fake_load)
    monkeypatch.setattr("app.ml.inference.engine.extract", fake_extract)
    return head_settings


def register(settings: Settings, head_type_id: str, num_classes: int, weights: dict) -> str:
    store = HeadInstanceStore(settings)
    instance = store.register(
        name=f"test {head_type_id}",
        kind="trained-here",
        head_type_id=head_type_id,
        task="",  # overwritten below via the spec; irrelevant to these assertions
        backbone_id="dinov2-small",
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


def detector_weights(num_classes: int) -> dict[str, torch.Tensor]:
    return {
        "classifier.weight": torch.randn(num_classes, EMBED, 1, 1),
        "classifier.bias": torch.randn(num_classes),
        "box_regressor.weight": torch.randn(4, EMBED, 1, 1),
        "box_regressor.bias": torch.randn(4),
        "centerness.weight": torch.randn(1, EMBED, 1, 1),
        "centerness.bias": torch.randn(1),
    }


def segmenter_weights(num_classes: int) -> dict[str, torch.Tensor]:
    return {
        "classifier.weight": torch.randn(num_classes, EMBED, 1, 1),
        "classifier.bias": torch.randn(num_classes),
    }


class TestClassification:
    def test_returns_scores_over_the_class_list(self, stubbed: Settings) -> None:
        instance_id = register(stubbed, "linear-classifier", 3, classifier_weights(3))
        prediction = run_inference(
            Image.new("RGB", (640, 480)), "dinov2-small", instance_id, settings=stubbed
        )

        assert prediction.render_hint == "labels"
        assert prediction.task == "classification"
        scores = prediction.payload["scores"]
        assert isinstance(scores, list) and len(scores) == 3
        assert sum(scores) == pytest.approx(1.0, abs=1e-4)

    def test_top_labels_uses_the_training_class_order(self, stubbed: Settings) -> None:
        instance_id = register(stubbed, "linear-classifier", 3, classifier_weights(3))
        prediction = run_inference(
            Image.new("RGB", (300, 300)), "dinov2-small", instance_id, settings=stubbed
        )
        top = prediction.top_labels(3)
        assert {name for name, _ in top} == {"class0", "class1", "class2"}


class TestDetection:
    def test_boxes_are_in_source_coordinates(self, stubbed: Settings) -> None:
        """The whole point of the feature: numbers the viewer can draw directly."""
        instance_id = register(stubbed, "dense-detector", 2, detector_weights(2))
        prediction = run_inference(
            Image.new("RGB", (900, 300)),
            "dinov2-small",
            instance_id,
            settings=stubbed,
            score_threshold=0.0,
        )

        assert prediction.render_hint == "boxes"
        assert prediction.boxes, "expected at least one box at threshold 0"
        for x, y, w, h in prediction.boxes:
            assert 0 <= x <= 900 and 0 <= y <= 300
            assert x + w <= 900 + 1 and y + h <= 300 + 1

    def test_threshold_filters_boxes(self, stubbed: Settings) -> None:
        instance_id = register(stubbed, "dense-detector", 2, detector_weights(2))
        kwargs = dict(settings=stubbed)
        image = Image.new("RGB", (400, 400))
        loose = run_inference(image, "dinov2-small", instance_id, score_threshold=0.0, **kwargs)
        strict = run_inference(image, "dinov2-small", instance_id, score_threshold=1.1, **kwargs)

        assert len(strict.boxes) == 0
        assert len(loose.boxes) >= len(strict.boxes)

    def test_payload_arrays_stay_aligned(self, stubbed: Settings) -> None:
        """Boxes, scores and classes are read positionally by the renderer."""
        instance_id = register(stubbed, "dense-detector", 2, detector_weights(2))
        prediction = run_inference(
            Image.new("RGB", (500, 500)),
            "dinov2-small",
            instance_id,
            settings=stubbed,
            score_threshold=0.0,
        )
        payload = prediction.payload
        assert len(payload["boxes"]) == len(payload["scores"]) == len(payload["classes"])


class TestSegmentation:
    def test_mask_is_returned_at_source_resolution(self, stubbed: Settings) -> None:
        instance_id = register(stubbed, "linear-segmenter", 4, segmenter_weights(4))
        prediction = run_inference(
            Image.new("RGB", (640, 360)), "dinov2-small", instance_id, settings=stubbed
        )

        assert prediction.render_hint == "masks"
        assert prediction.payload["height"] == 360
        assert prediction.payload["width"] == 640
        assert len(prediction.payload["mask"]) == 360
        assert len(prediction.payload["mask"][0]) == 640

    def test_mask_holds_only_real_class_indices(self, stubbed: Settings) -> None:
        """Nearest-neighbour inversion must not invent ids between classes."""
        instance_id = register(stubbed, "linear-segmenter", 4, segmenter_weights(4))
        prediction = run_inference(
            Image.new("RGB", (320, 240)), "dinov2-small", instance_id, settings=stubbed
        )
        assert prediction.mask_classes <= {0, 1, 2, 3}


class TestGuards:
    def test_backbone_mismatch_is_refused_with_a_reason(self, stubbed: Settings) -> None:
        instance_id = register(stubbed, "linear-classifier", 2, classifier_weights(2))
        with pytest.raises(BackboneMismatchError) as caught:
            run_inference(
                Image.new("RGB", (200, 200)), "dinov2-base", instance_id, settings=stubbed
            )
        message = str(caught.value)
        assert "dinov2-small" in message and "dinov2-base" in message

    def test_unknown_instance_raises(self, stubbed: Settings) -> None:
        from app.ml.heads.store import HeadInstanceNotFoundError

        with pytest.raises(HeadInstanceNotFoundError):
            run_inference(
                Image.new("RGB", (200, 200)), "dinov2-small", "nope", settings=stubbed
            )


class TestContract:
    def test_prediction_carries_provenance_not_a_path(self, stubbed: Settings) -> None:
        """Doc 12's rule reaches the viewer: a head is named, never filed."""
        instance_id = register(stubbed, "linear-classifier", 2, classifier_weights(2))
        prediction = run_inference(
            Image.new("RGB", (200, 200)), "dinov2-small", instance_id, settings=stubbed
        )
        assert prediction.instance_id == instance_id
        assert prediction.head_name
        assert ".safetensors" not in prediction.head_name

    def test_grid_and_timing_are_reported(self, stubbed: Settings) -> None:
        instance_id = register(stubbed, "linear-classifier", 2, classifier_weights(2))
        prediction = run_inference(
            Image.new("RGB", (224, 224)), "dinov2-small", instance_id, settings=stubbed
        )
        assert prediction.grid[0] > 0 and prediction.grid[1] > 0
        assert prediction.elapsed_ms >= 0

"""Shared setup for the three inference routes' API tests.

The routes are tested in separate modules — one responsibility per file — but they need
the same stubbed backbone and the same throwaway head store, and a second copy of this
fixture is how two of them quietly drift apart.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
import torch
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app
from app.ml.heads.store import HeadInstanceStore
from tests.head_testkit import install_fake_backbone

EMBED = 32


def stub_inference_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[TestClient]:
    """A TestClient with a fake backbone installed and its forward pass stubbed.

    Loading dinov2-small here would make every route test depend on a 168 MB download;
    the doc-07 tensor contract is what the routes consume and it is expressible in a stub.
    Integration against real weights happens outside the suite, which is where every real
    bug in this project has come from.
    """
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_connection()

    from app.ml.backbone import BackboneCapabilities, BackboneFeatures

    install_fake_backbone(get_settings(), "dinov2-small", EMBED)
    capabilities = BackboneCapabilities(
        model_id="dinov2-small",
        family="dinov2",
        patch_size=14,
        embed_dim=EMBED,
        num_prefix_tokens=1,
        num_layers=12,
        image_size=518,
    )

    class StubBackbone:
        def __init__(self) -> None:
            self.capabilities = capabilities
            self.device = "cpu"

    def fake_extract(backbone: object, pixel_values: torch.Tensor) -> BackboneFeatures:
        rows = int(pixel_values.shape[-2]) // 14
        cols = int(pixel_values.shape[-1]) // 14
        return BackboneFeatures(
            cls=torch.randn(1, EMBED),
            patches=torch.randn(1, EMBED, rows, cols),
            grid=(rows, cols),
        )

    # Patched on `compose`: since feature 18 that is where the backbone pass is paid for,
    # and `/inference` reaches it by delegating rather than running its own.
    monkeypatch.setattr("app.ml.inference.compose.load_backbone", lambda *a, **k: StubBackbone())
    monkeypatch.setattr("app.ml.inference.compose.extract", fake_extract)

    with TestClient(create_app()) as test_client:
        yield test_client
    reset_connection()
    get_settings.cache_clear()


def add_classifier(num_classes: int = 3, name: str = "Shapes classifier") -> str:
    instance = HeadInstanceStore().register(
        name=name,
        kind="trained-here",
        head_type_id="linear-classifier",
        task="classification",
        backbone_id="dinov2-small",
        backbone_family="dinov2",
        embed_dim=EMBED,
        num_classes=num_classes,
        weights={
            "linear.weight": torch.randn(num_classes, EMBED),
            "linear.bias": torch.randn(num_classes),
        },
        class_names=tuple(f"class{i}" for i in range(num_classes)),
    )
    return instance.id


def add_segmenter(num_classes: int = 3, name: str = "Shapes segmenter") -> str:
    """A dense head — aspect-preserve @ 448, so it cannot share a pass with a classifier."""
    instance = HeadInstanceStore().register(
        name=name,
        kind="trained-here",
        head_type_id="linear-segmenter",
        task="segmentation",
        backbone_id="dinov2-small",
        backbone_family="dinov2",
        embed_dim=EMBED,
        num_classes=num_classes,
        weights={
            "classifier.weight": torch.randn(num_classes, EMBED, 1, 1),
            "classifier.bias": torch.randn(num_classes),
        },
        class_names=tuple(f"class{i}" for i in range(num_classes)),
    )
    return instance.id


def write_image(path: Path, size: tuple[int, int] = (320, 240)) -> str:
    Image.new("RGB", size, (120, 90, 60)).save(path)
    return str(path)


def add_detector(num_classes: int = 2, name: str = "Shapes detector") -> str:
    """A `boxes`-hint head — the only kind Wave 4's expert annotator will accept.

    Weight shapes follow DetectionHead in app/ml/heads/modules.py: a 1x1 conv classifier,
    a four-channel box regressor for the l/t/r/b distances, and a single centerness
    channel.
    """
    instance = HeadInstanceStore().register(
        name=name,
        kind="trained-here",
        head_type_id="dense-detector",
        task="detection",
        backbone_id="dinov2-small",
        backbone_family="dinov2",
        embed_dim=EMBED,
        num_classes=num_classes,
        weights={
            "classifier.weight": torch.randn(num_classes, EMBED, 1, 1),
            "classifier.bias": torch.randn(num_classes),
            "box_regressor.weight": torch.randn(4, EMBED, 1, 1),
            "box_regressor.bias": torch.randn(4),
            "centerness.weight": torch.randn(1, EMBED, 1, 1),
            "centerness.bias": torch.randn(1),
        },
        class_names=tuple(f"object{i}" for i in range(num_classes)),
    )
    return instance.id

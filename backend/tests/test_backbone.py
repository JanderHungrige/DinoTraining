"""Tests for frozen-backbone loading, the capability descriptor and token splitting.

No weights are loaded here. What is exercised is the config.json → capabilities read,
the install/kind gates, and the token-splitting arithmetic that every head depends on —
which is where a wrong prefix-token count would silently misalign the patch grid.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest
import torch

from app.core.config import get_settings
from app.ml.backbone import (
    BackboneCapabilities,
    FeatureShapeError,
    ModelNotInstalledError,
    _grid_dims,
    _split_tokens,
    clear_cache,
    load_backbone,
    read_capabilities,
)


@pytest.fixture(autouse=True)
def _clean_cache() -> Iterator[None]:
    clear_cache()
    yield
    clear_cache()


def write_config(
    root: Path,
    model_id: str,
    *,
    patch_size: int = 14,
    hidden_size: int = 768,
    num_hidden_layers: int = 12,
    image_size: int = 518,
    registers: int | None = None,
) -> Path:
    """Write a minimal HF-style config.json for one model in the cache root."""
    directory = root / model_id
    directory.mkdir(parents=True, exist_ok=True)
    config: dict[str, object] = {
        "patch_size": patch_size,
        "hidden_size": hidden_size,
        "num_hidden_layers": num_hidden_layers,
        "image_size": image_size,
    }
    if registers is not None:
        config["num_register_tokens"] = registers
    (directory / "config.json").write_text(json.dumps(config))
    return directory


def install(directory: Path) -> None:
    """Make a model dir look installed — weights present, per paths.is_installed."""
    (directory / "model.safetensors").write_bytes(b"not real weights")


@pytest.fixture
def cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path))
    get_settings.cache_clear()
    yield tmp_path
    get_settings.cache_clear()


class TestGridDims:
    def test_divides_by_patch_size(self) -> None:
        assert _grid_dims(224, 224, 14) == (16, 16)

    def test_handles_non_square_input(self) -> None:
        """Dense heads must work on non-square crops; Gh and Gw are independent."""
        assert _grid_dims(224, 112, 14) == (16, 8)

    def test_rejects_indivisible_height(self) -> None:
        with pytest.raises(ValueError, match="divisible"):
            _grid_dims(225, 224, 14)

    def test_rejects_indivisible_width(self) -> None:
        with pytest.raises(ValueError, match="divisible"):
            _grid_dims(224, 225, 14)

    def test_patch16_backbone(self) -> None:
        assert _grid_dims(256, 256, 16) == (16, 16)


class TestSplitTokens:
    def test_splits_cls_and_patches(self) -> None:
        hidden = torch.zeros(2, 1 + 16, 8)
        cls, patches = _split_tokens(hidden, num_prefix_tokens=1, grid=(4, 4))
        assert cls.shape == (2, 8)
        assert patches.shape == (2, 8, 4, 4)

    def test_cls_is_the_first_token(self) -> None:
        hidden = torch.zeros(1, 1 + 4, 3)
        hidden[0, 0, :] = 7.0
        cls, _ = _split_tokens(hidden, num_prefix_tokens=1, grid=(2, 2))
        assert torch.equal(cls[0], torch.full((3,), 7.0))

    def test_skips_register_tokens(self) -> None:
        """DINOv3 registers sit between CLS and the patches; slicing at 1 misaligns."""
        hidden = torch.zeros(1, 1 + 4 + 4, 3)
        hidden[0, 5:, :] = 1.0  # the real patch tokens, after CLS + 4 registers
        _, patches = _split_tokens(hidden, num_prefix_tokens=5, grid=(2, 2))
        assert torch.equal(patches, torch.ones(1, 3, 2, 2))

    def test_patches_are_channels_first(self) -> None:
        """Heads are plain Conv2d, so the grid must be (B, D, Gh, Gw) not (B, Gh, Gw, D)."""
        hidden = torch.arange(1 * 4 * 2, dtype=torch.float32).reshape(1, 4, 2)
        _, patches = _split_tokens(hidden, num_prefix_tokens=0, grid=(2, 2))
        assert patches.shape == (1, 2, 2, 2)
        # token 0 is [0, 1] → channel 0 at (0,0) is 0, channel 1 at (0,0) is 1
        assert patches[0, 0, 0, 0] == 0.0
        assert patches[0, 1, 0, 0] == 1.0

    def test_grid_mismatch_raises_with_both_counts(self) -> None:
        """The loud failure that catches a wrong prefix count instead of training garbage."""
        hidden = torch.zeros(1, 1 + 15, 8)
        with pytest.raises(FeatureShapeError, match="15.*16|16.*15"):
            _split_tokens(hidden, num_prefix_tokens=1, grid=(4, 4))

    def test_preserves_batch_dimension(self) -> None:
        hidden = torch.zeros(5, 1 + 9, 6)
        cls, patches = _split_tokens(hidden, num_prefix_tokens=1, grid=(3, 3))
        assert cls.shape[0] == 5
        assert patches.shape[0] == 5


class TestReadCapabilities:
    def test_reads_from_config_json(self, cache: Path) -> None:
        install(write_config(cache, "dinov2-base"))
        caps = read_capabilities("dinov2-base")
        assert caps == BackboneCapabilities(
            model_id="dinov2-base",
            family="dinov2",
            patch_size=14,
            embed_dim=768,
            num_prefix_tokens=1,
            num_layers=12,
            image_size=518,
        )

    def test_register_tokens_raise_the_prefix_count(self, cache: Path) -> None:
        install(write_config(cache, "dinov3-vitb16", patch_size=16, registers=4))
        assert read_capabilities("dinov3-vitb16").num_prefix_tokens == 5

    def test_absent_registers_mean_one_prefix_token(self, cache: Path) -> None:
        install(write_config(cache, "dinov2-small", hidden_size=384))
        assert read_capabilities("dinov2-small").num_prefix_tokens == 1

    def test_does_not_load_weights(self, cache: Path) -> None:
        """Capabilities must be cheap — the Admin tab reads every installed backbone."""
        directory = write_config(cache, "dinov2-base")
        (directory / "model.safetensors").write_bytes(b"definitely not a valid checkpoint")
        assert read_capabilities("dinov2-base").embed_dim == 768

    def test_uninstalled_model_raises(self, cache: Path) -> None:
        with pytest.raises(ModelNotInstalledError):
            read_capabilities("dinov2-base")

    def test_unknown_model_raises_lookup_error(self, cache: Path) -> None:
        with pytest.raises(LookupError):
            read_capabilities("not-a-model")

    def test_a_detector_is_not_a_backbone(self, cache: Path) -> None:
        install(write_config(cache, "grounding-dino-tiny"))
        with pytest.raises(ValueError, match="not a backbone"):
            read_capabilities("grounding-dino-tiny")

    def test_malformed_config_raises(self, cache: Path) -> None:
        directory = write_config(cache, "dinov2-base")
        (directory / "config.json").write_text("{ not json")
        install(directory)
        with pytest.raises(ValueError, match="config"):
            read_capabilities("dinov2-base")

    def test_config_missing_required_field_raises(self, cache: Path) -> None:
        directory = write_config(cache, "dinov2-base")
        (directory / "config.json").write_text(json.dumps({"patch_size": 14}))
        install(directory)
        with pytest.raises(ValueError, match="hidden_size"):
            read_capabilities("dinov2-base")


class TestLoadBackbone:
    def test_uninstalled_model_raises(self, cache: Path) -> None:
        with pytest.raises(ModelNotInstalledError):
            load_backbone("dinov2-base")

    def test_unknown_model_raises_lookup_error(self, cache: Path) -> None:
        with pytest.raises(LookupError):
            load_backbone("not-a-model")

    def test_a_detector_is_not_a_backbone(self, cache: Path) -> None:
        with pytest.raises(ValueError, match="not a backbone"):
            load_backbone("grounding-dino-tiny")

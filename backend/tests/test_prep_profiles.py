"""What each model does to an image, read from its own processor config (doc 81)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.prep.profiles import get_profile, list_profiles


@pytest.fixture(autouse=True)
def _cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    yield tmp_path / "models"
    get_settings.cache_clear()


def _install(cache: Path, model_id: str, size: dict[str, int]) -> None:
    (cache / model_id).mkdir(parents=True)
    (cache / model_id / "preprocessor_config.json").write_text(json.dumps({"size": size}))


def test_a_letterboxed_model_scales_by_its_long_edge() -> None:
    profile = get_profile("rf-detr-nano")
    # A 2464x1600 frame letterboxed to 384 px: every pixel becomes 0.156 px.
    assert profile.scale_for(2464, 1600) == pytest.approx(384 / 2464)


def test_the_installed_processor_config_wins_over_the_default(_cache: Path) -> None:
    _install(_cache, "rf-detr-nano", {"height": 560, "width": 560})
    assert get_profile("rf-detr-nano").input_size == 560


def test_a_shortest_edge_processor_is_capped_by_its_longest_edge(_cache: Path) -> None:
    _install(_cache, "rf-detr-nano", {"shortest_edge": 800, "longest_edge": 1333})
    profile = get_profile("rf-detr-nano")
    assert profile.fit == "shortest-edge"
    # 800 / 1600 would make the long edge 1232, under the 1333 cap.
    assert profile.scale_for(2464, 1600) == pytest.approx(0.5)
    # A very wide image hits the cap instead: 1333 / 4000.
    assert profile.scale_for(4000, 1000) == pytest.approx(1333 / 4000)


def test_the_smallest_visible_object_is_two_feature_cells() -> None:
    assert get_profile("head-detection-dinov2").min_visible_px == 28  # patch 14


def test_every_profile_can_be_listed_and_an_unknown_one_is_refused() -> None:
    assert {p.id for p in list_profiles()} >= {"rf-detr-nano", "head-detection-dinov2"}
    with pytest.raises(KeyError):
        get_profile("no-such-model")

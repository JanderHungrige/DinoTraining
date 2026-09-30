"""The imbalance recommendation, over hand-built facts and through the API (doc 86)."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app
from app.prep.balance_plan import plan_balance
from app.prep.profiles import get_profile
from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts


def facts(per_image: list[list[str]]) -> DatasetFacts:
    return DatasetFacts(
        dataset_id="d",
        images=[ImageFacts(i, f"/i/{i}.jpg", 400, 400, None) for i in range(len(per_image))],
        annotations=[
            AnnotationFacts(i, "box", "positive", cls, cls, 40, 40, 0, 0)
            for i, classes in enumerate(per_image)
            for cls in classes
        ],
    )


# Blood cells in miniature: every image full of red cells, platelets in a few.
CELLS = [["rbc"] * 12 for _ in range(36)] + [["rbc"] * 12 + ["platelet"] for _ in range(4)]


def test_boxes_with_unequal_classes_are_sampled_and_the_effect_is_shown() -> None:
    plan = plan_balance(facts(CELLS), get_profile("head-detection-dinov2"))
    assert plan.ratio == 120.0
    assert plan.recommended == "balanced-sampling"
    assert "background" in plan.reason
    by_name = {c.name: c for c in plan.classes}
    assert by_name["platelet"].repeat == pytest.approx(10**0.5, abs=0.01)  # sqrt(40 / 4)
    assert by_name["platelet"].weight > by_name["rbc"].weight
    assert any("platelet" in w and "only 4" in w for w in plan.warnings)
    assert plan.applies_to_training is True


def test_a_rare_class_that_shares_every_picture_is_weighted_not_sampled() -> None:
    # Blood cells as measured: platelets in about half the pictures, always beside many
    # red cells. Sampling would repeat the red cells too (1.41×); weighting is the remedy.
    shared = [["rbc"] * 12 + ["platelet"] for _ in range(20)] + [["rbc"] * 12 for _ in range(20)]
    plan = plan_balance(facts(shared), get_profile("head-detection-dinov2"))
    assert plan.ratio == 24.0
    assert plan.recommended == "weighted-loss"
    assert "alongside" in plan.reason
    by_name = {c.name: c for c in plan.classes}
    assert by_name["platelet"].weight / by_name["rbc"].weight == pytest.approx(24**0.5, rel=0.01)


def test_whole_image_labels_are_weighted_instead() -> None:
    plan = plan_balance(facts(CELLS), get_profile("head-classification-dinov2"))
    assert plan.recommended == "weighted-loss"


def test_nearly_equal_classes_are_left_alone() -> None:
    even = [["a"], ["a"], ["b"]] * 10
    plan = plan_balance(facts(even), get_profile("head-detection-dinov2"))
    assert plan.recommended == "none" and plan.warnings == []


def test_a_fine_tune_target_says_the_strategy_is_not_applied_yet() -> None:
    assert plan_balance(facts(CELLS), get_profile("rf-detr-nano")).applies_to_training is False


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
    get_settings.cache_clear()


def test_the_api_plans_and_refuses_with_reasons(client: TestClient) -> None:
    dataset_id = client.post("/api/v1/datasets", json={"name": "Cells"}).json()["id"]
    box = {"label": "positive", "provenance": "hand-drawn", "x": 1, "y": 1, "w": 5, "h": 5}
    for i, cls in enumerate(["rbc"] * 8 + ["platelet"]):
        body = {"path": f"/c/{i}.jpg", "width": 50, "height": 50, "boxes": [box | {"prompt": cls}]}
        client.put(f"/api/v1/datasets/{dataset_id}/images", json=body)
    url = f"/api/v1/datasets/{dataset_id}/balance"
    plan = client.get(url, params={"target": "head-detection-dinov2"}).json()
    assert plan["ratio"] == 8.0 and plan["recommended"] == "balanced-sampling"
    assert client.get(url, params={"target": "nope"}).status_code == 422
    assert (
        client.get("/api/v1/datasets/x/balance", params={"target": "rf-detr-nano"}).status_code
        == 404
    )

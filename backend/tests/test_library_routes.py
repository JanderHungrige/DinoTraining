"""Routes the organize tab needs (docs 50, 51).

Two of them did not exist: a dataset could not list its own images, and a fine-tuned model
could not be deleted at all — its store had a `delete` with nothing calling it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import get_settings
from app.datasets.models import Box, ImageAnnotation
from app.datasets.store import DatasetStore
from app.main import app
from app.ml.foundation.build import build_foundation, reset_cache
from app.ml.foundation.instances import FoundationInstanceStore


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    reset_cache()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _dataset_with_image(tmp_path: Path) -> tuple[str, str]:
    store = DatasetStore()
    info = store.create("Rails", None, copy_images=False)
    path = tmp_path / "frame.png"
    Image.new("RGB", (60, 40)).save(path)
    store.replace_image_boxes(
        info.id,
        ImageAnnotation(
            path=str(path),
            width=60,
            height=40,
            boxes=[
                Box(label="positive", provenance="imported", x=1, y=1, w=5, h=5, prompt="p")
            ],
        ),
    )
    return info.id, str(path)


class TestListingADatasetsImages:
    def test_it_returns_the_stored_paths(self, client: TestClient, tmp_path: Path) -> None:
        dataset_id, path = _dataset_with_image(tmp_path)
        body = client.get(f"/api/v1/datasets/{dataset_id}/images").json()
        assert [image["path"] for image in body["images"]] == [path]

    def test_it_carries_the_size(self, client: TestClient, tmp_path: Path) -> None:
        # Deriving it client-side would mean opening every image just to render a list.
        dataset_id, _ = _dataset_with_image(tmp_path)
        image = client.get(f"/api/v1/datasets/{dataset_id}/images").json()["images"][0]
        assert (image["width"], image["height"]) == (60, 40)

    def test_it_carries_the_boxes_the_dataset_already_has(
        self, client: TestClient, tmp_path: Path
    ) -> None:
        """Picking a dataset as a source means "carry on working on this", so the review
        surface needs its boxes the moment it opens. One call per image would put a
        request behind every press of the Next key."""
        dataset_id, _ = _dataset_with_image(tmp_path)
        image = client.get(f"/api/v1/datasets/{dataset_id}/images").json()["images"][0]
        assert len(image["boxes"]) == 1
        assert image["boxes"][0]["provenance"] == "imported"
        assert image["boxes"][0]["prompt"] == "p"

    def test_an_empty_dataset_lists_nothing_rather_than_failing(
        self, client: TestClient
    ) -> None:
        info = DatasetStore().create("Empty", None, copy_images=False)
        assert client.get(f"/api/v1/datasets/{info.id}/images").json()["images"] == []

    def test_an_unknown_dataset_is_a_404(self, client: TestClient) -> None:
        assert client.get("/api/v1/datasets/nope/images").status_code == 404


class TestDeletingAFineTunedModel:
    def _save(self) -> str:
        return FoundationInstanceStore().save(
            existing_id=None,
            name="Rail detector",
            base_model_id="rf-detr-nano",
            dataset_ids=("d1",),
            class_names=("person",),
            metrics={"map": 0.5},
            epochs_trained=6,
            save=lambda directory: (directory / "model.safetensors").write_bytes(b"\x00"),
        ).id

    def test_it_removes_the_model(self, client: TestClient) -> None:
        instance_id = self._save()
        assert client.delete(f"/api/v1/foundation/instances/{instance_id}").status_code == 200
        assert FoundationInstanceStore().list_all() == []

    def test_it_disappears_from_the_listing(self, client: TestClient) -> None:
        instance_id = self._save()
        client.delete(f"/api/v1/foundation/instances/{instance_id}")
        listed = client.get("/api/v1/foundation").json()["foundations"]
        assert instance_id not in [entry["id"] for entry in listed]

    def test_an_unknown_id_is_a_404_not_a_silent_success(self, client: TestClient) -> None:
        # "It was already gone" and "you deleted the wrong thing" must not look the same.
        assert client.delete("/api/v1/foundation/instances/nope").status_code == 404

    def test_a_traversal_id_is_refused(self, client: TestClient) -> None:
        response = client.delete("/api/v1/foundation/instances/..%2F..%2Fetc")
        assert response.status_code in {400, 404}
        assert response.status_code != 500

    def test_a_catalogue_model_cannot_be_deleted_here(self, client: TestClient) -> None:
        # Those are downloads managed in Admin / Models; deleting one here would silently
        # disagree with what that tab says is installed.
        assert client.delete("/api/v1/foundation/instances/rf-detr-nano").status_code == 404

    def test_the_cached_implementation_is_dropped(self, client: TestClient) -> None:
        """Without this, a model whose weights have just been deleted keeps answering from
        memory until the process restarts — with results that look entirely normal."""
        instance_id = self._save()
        from app.ml.foundation import build as build_module

        build_module._CACHE[instance_id] = object()  # type: ignore[assignment]
        client.delete(f"/api/v1/foundation/instances/{instance_id}")
        assert instance_id not in build_module._CACHE


def test_build_foundation_is_importable() -> None:
    # Guards the import the delete route needs; a NameError there would be a 500.
    assert callable(build_foundation)

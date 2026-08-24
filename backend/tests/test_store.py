"""Tests for DatasetStore — creation, the replace-not-append write path, counters."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.datasets.db import reset_connection
from app.datasets.models import Box, ImageAnnotation
from app.datasets.store import DatasetNotFoundError, DatasetStore, dataset_dir


@pytest.fixture
def store(tmp_path: Path) -> Iterator[DatasetStore]:
    reset_connection()
    yield DatasetStore(Settings(_env_file=None, data_dir=tmp_path))
    reset_connection()


def box(label: str = "positive", provenance: str = "grounding-dino", **kwargs: float) -> Box:
    defaults = {"x": 10.0, "y": 10.0, "w": 20.0, "h": 20.0}
    defaults.update(kwargs)
    return Box(label=label, provenance=provenance, **defaults)


def annotation(*boxes: Box, path: str = "/images/a.jpg") -> ImageAnnotation:
    return ImageAnnotation(path=path, width=200, height=200, boxes=list(boxes))


class TestCreate:
    def test_returns_a_generated_id(self, store: DatasetStore) -> None:
        info = store.create("Cats", None, False)
        assert len(info.id) == 32
        assert info.name == "Cats"

    def test_ids_are_unique(self, store: DatasetStore) -> None:
        assert store.create("A", None, False).id != store.create("B", None, False).id

    def test_writes_the_native_manifest(self, store: DatasetStore, tmp_path: Path) -> None:
        info = store.create("Cats", "a cat", False)
        settings = Settings(_env_file=None, data_dir=tmp_path)
        manifest = dataset_dir(info.id, settings) / "dataset.json"
        assert manifest.is_file()
        assert '"dinotraining-dataset"' in manifest.read_text()

    def test_new_dataset_has_zero_counts(self, store: DatasetStore) -> None:
        assert store.create("Cats", None, False).counts.images == 0

    def test_listing_is_newest_first(self, store: DatasetStore) -> None:
        store.create("A", None, False)
        second = store.create("B", None, False)
        assert store.list_all()[0].id in {second.id, store.list_all()[0].id}
        assert len(store.list_all()) == 2

    def test_get_unknown_raises(self, store: DatasetStore) -> None:
        with pytest.raises(DatasetNotFoundError):
            store.get("nope")


class TestReplaceImageBoxes:
    def test_stores_boxes_and_counts_them(self, store: DatasetStore) -> None:
        dataset = store.create("Cats", None, False)
        counts = store.replace_image_boxes(
            dataset.id, annotation(box("positive"), box("negative"), box("unclear"))
        )
        assert counts.images == 1
        assert counts.boxes == 3
        assert (counts.positive, counts.negative, counts.unclear) == (1, 1, 1)

    def test_second_save_replaces_rather_than_appends(self, store: DatasetStore) -> None:
        """Re-reviewing an image must not leave the old verdicts behind."""
        dataset = store.create("Cats", None, False)
        store.replace_image_boxes(dataset.id, annotation(box("positive"), box("positive")))
        counts = store.replace_image_boxes(dataset.id, annotation(box("negative")))

        assert counts.images == 1
        assert counts.boxes == 1
        assert counts.positive == 0
        assert counts.negative == 1

    def test_distinct_images_accumulate(self, store: DatasetStore) -> None:
        dataset = store.create("Cats", None, False)
        store.replace_image_boxes(dataset.id, annotation(box(), path="/images/a.jpg"))
        counts = store.replace_image_boxes(dataset.id, annotation(box(), path="/images/b.jpg"))
        assert counts.images == 2
        assert counts.boxes == 2

    def test_saving_zero_boxes_still_records_the_image(self, store: DatasetStore) -> None:
        """An image the user reviewed and found nothing in is still progress."""
        dataset = store.create("Cats", None, False)
        counts = store.replace_image_boxes(dataset.id, annotation())
        assert counts.images == 1
        assert counts.boxes == 0

    def test_unknown_dataset_raises(self, store: DatasetStore) -> None:
        with pytest.raises(DatasetNotFoundError):
            store.replace_image_boxes("nope", annotation(box()))

    def test_provenance_and_score_round_trip(self, store: DatasetStore) -> None:
        dataset = store.create("Cats", None, False)
        proposed = Box(
            label="positive", provenance="grounding-dino", x=1, y=2, w=3, h=4, score=0.87
        )
        store.replace_image_boxes(dataset.id, annotation(proposed))

        stored = store.image_annotations(dataset.id)[0][4][0]
        assert stored.provenance == "grounding-dino"
        assert stored.score == pytest.approx(0.87)


class TestValidation:
    def test_box_outside_the_frame_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="outside"):
            ImageAnnotation(
                path="/a.jpg",
                width=100,
                height=100,
                boxes=[Box(label="positive", provenance="hand-drawn", x=90, y=0, w=20, h=10)],
            )

    def test_zero_width_box_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Box(label="positive", provenance="hand-drawn", x=0, y=0, w=0, h=10)

    def test_invalid_label_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Box(label="maybe", provenance="hand-drawn", x=0, y=0, w=1, h=1)

    def test_score_above_one_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            Box(label="positive", provenance="grounding-dino", x=0, y=0, w=1, h=1, score=1.5)

    def test_box_exactly_at_the_edge_is_allowed(self) -> None:
        annotation = ImageAnnotation(
            path="/a.jpg",
            width=100,
            height=100,
            boxes=[Box(label="positive", provenance="hand-drawn", x=90, y=90, w=10, h=10)],
        )
        assert len(annotation.boxes) == 1


class TestDelete:
    def test_removes_rows_and_directory(self, store: DatasetStore, tmp_path: Path) -> None:
        settings = Settings(_env_file=None, data_dir=tmp_path)
        dataset = store.create("Cats", None, False)
        store.replace_image_boxes(dataset.id, annotation(box()))
        directory = dataset_dir(dataset.id, settings)

        assert store.delete(dataset.id) is True
        assert not directory.exists()
        assert store.list_all() == []

    def test_deleting_unknown_returns_false(self, store: DatasetStore) -> None:
        assert store.delete("nope") is False

    def test_delete_leaves_other_datasets_alone(self, store: DatasetStore) -> None:
        keep = store.create("Keep", None, False)
        drop = store.create("Drop", None, False)
        store.delete(drop.id)
        assert [d.id for d in store.list_all()] == [keep.id]


class TestCopyImages:
    def test_copies_the_file_into_the_dataset(
        self, store: DatasetStore, tmp_path: Path
    ) -> None:
        source = tmp_path / "source.jpg"
        source.write_bytes(b"jpegbytes")
        dataset = store.create("Cats", None, copy_images=True)

        store.replace_image_boxes(dataset.id, annotation(box(), path=str(source)))

        stored_path = Path(store.image_annotations(dataset.id)[0][1])
        assert stored_path.is_file()
        assert stored_path.read_bytes() == b"jpegbytes"
        assert stored_path != source

    def test_referencing_mode_keeps_the_original_path(
        self, store: DatasetStore, tmp_path: Path
    ) -> None:
        source = tmp_path / "source.jpg"
        source.write_bytes(b"jpegbytes")
        dataset = store.create("Cats", None, copy_images=False)

        store.replace_image_boxes(dataset.id, annotation(box(), path=str(source)))

        assert store.image_annotations(dataset.id)[0][1] == str(source)

    def test_a_missing_source_does_not_lose_the_labels(
        self, store: DatasetStore
    ) -> None:
        """Failing the save would throw away work the user just did."""
        dataset = store.create("Cats", None, copy_images=True)
        counts = store.replace_image_boxes(
            dataset.id, annotation(box(), path="/absent/ghost.jpg")
        )
        assert counts.boxes == 1

"""Reading a third-party COCO export.

The test that matters most is `TestCategoriesResolveByName`. Every other rule here is
ordinary input handling; that one encodes a trap the three reference datasets disagree
about, where the wrong rule loses data *and still reports success*.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from app.datasets.coco_import import (
    COCO_FILENAME,
    find_coco_files,
    import_coco_dataset,
    load_split,
    normalise_class,
)
from app.datasets.store import DatasetStore


def _write_image(path: Path, width: int = 40, height: int = 30) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (width, height), (10, 20, 30)).save(path)


def _coco(
    categories: list[dict[str, Any]],
    images: list[dict[str, Any]],
    annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "info": {},
        "licenses": [],
        "categories": categories,
        "images": images,
        "annotations": annotations,
    }


def _write_split(directory: Path, payload: dict[str, Any], *, make_images: bool = True) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / COCO_FILENAME).write_text(json.dumps(payload))
    if make_images:
        for entry in payload["images"]:
            _write_image(directory / entry["file_name"], entry["width"], entry["height"])
    return directory / COCO_FILENAME


#: The Roboflow shape: a placeholder super-category at id 0 that nothing references.
_PLACEHOLDER_STYLE = _coco(
    categories=[
        {"id": 0, "name": "thermal-dogs-n-people", "supercategory": "none"},
        {"id": 1, "name": "dog", "supercategory": "thermal-dogs-n-people"},
        {"id": 2, "name": "person", "supercategory": "thermal-dogs-n-people"},
    ],
    images=[{"id": 0, "file_name": "a.jpg", "width": 40, "height": 30}],
    annotations=[
        {"id": 1, "image_id": 0, "category_id": 1, "bbox": [1, 2, 10, 8], "area": 80},
        {"id": 2, "image_id": 0, "category_id": 2, "bbox": [20, 4, 6, 12], "area": 72},
    ],
)

#: The other Roboflow shape: id 0 is a **real class**, and dropping it loses data.
_ZERO_IS_REAL_STYLE = _coco(
    categories=[
        {"id": 0, "name": "platelets", "supercategory": "cells"},
        {"id": 1, "name": "rbc", "supercategory": "cells"},
        {"id": 2, "name": "wbc", "supercategory": "cells"},
    ],
    images=[{"id": 0, "file_name": "b.jpg", "width": 40, "height": 30}],
    annotations=[
        {"id": 1, "image_id": 0, "category_id": 0, "bbox": [0, 0, 5, 5], "area": 25},
        {"id": 2, "image_id": 0, "category_id": 1, "bbox": [10, 10, 5, 5], "area": 25},
    ],
)


class TestCategoriesResolveByName:
    """The category-0 trap, from both sides.

    `thermal` and `chess` have a placeholder at id 0; `blood` has `platelets` there. Any
    rule phrased in terms of the *id* is right for one group and silently destructive for
    the other, so the importer resolves through the file's own `categories` list.
    """

    def test_an_unreferenced_placeholder_contributes_no_class(self, tmp_path: Path) -> None:
        path = _write_split(tmp_path / "train", _PLACEHOLDER_STYLE)
        split = load_split(path)
        prompts = {box.prompt for box in split.annotations[0].boxes}
        assert prompts == {"dog", "person"}
        assert "thermal-dogs-n-people" not in prompts

    def test_a_real_class_at_id_zero_survives(self, tmp_path: Path) -> None:
        # The regression this whole module exists for: skipping id 0 would drop every
        # platelet annotation, leave a plausible-looking dataset behind, and report success.
        path = _write_split(tmp_path / "train", _ZERO_IS_REAL_STYLE)
        split = load_split(path)
        boxes = split.annotations[0].boxes
        assert {box.prompt for box in boxes} == {"platelets", "rbc"}
        assert split.skipped_boxes == 0

    def test_an_unknown_category_id_is_skipped_and_counted(self, tmp_path: Path) -> None:
        payload = _coco(
            categories=[{"id": 1, "name": "dog"}],
            images=[{"id": 0, "file_name": "a.jpg", "width": 40, "height": 30}],
            annotations=[
                {"id": 1, "image_id": 0, "category_id": 1, "bbox": [0, 0, 5, 5]},
                {"id": 2, "image_id": 0, "category_id": 99, "bbox": [6, 6, 5, 5]},
            ],
        )
        split = load_split(_write_split(tmp_path / "train", payload))
        assert len(split.annotations[0].boxes) == 1
        assert split.skipped_boxes == 1

    def test_class_names_are_normalised_the_way_the_trainer_normalises_them(self) -> None:
        assert normalise_class("  Dog.  ") == "dog"
        assert normalise_class("black-bishop") == "black-bishop"


class TestBoxesAreCopiedNotConverted:
    def test_bbox_reaches_the_box_verbatim(self, tmp_path: Path) -> None:
        split = load_split(_write_split(tmp_path / "train", _PLACEHOLDER_STYLE))
        dog = next(box for box in split.annotations[0].boxes if box.prompt == "dog")
        assert (dog.x, dog.y, dog.w, dog.h) == (1.0, 2.0, 10.0, 8.0)

    def test_every_imported_box_is_positive_and_imported(self, tmp_path: Path) -> None:
        split = load_split(_write_split(tmp_path / "train", _PLACEHOLDER_STYLE))
        for box in split.annotations[0].boxes:
            assert box.label == "positive"
            assert box.provenance == "imported"
            assert box.score is None
            assert box.producer is None

    def test_dimensions_come_from_the_coco_file(self, tmp_path: Path) -> None:
        split = load_split(_write_split(tmp_path / "train", _PLACEHOLDER_STYLE))
        assert (split.annotations[0].width, split.annotations[0].height) == (40, 30)


class TestLossIsSkippedAndCounted:
    @pytest.mark.parametrize(
        ("bbox", "why"),
        [
            ([35, 0, 10, 5], "reaches past the right edge"),
            ([0, 28, 5, 10], "reaches past the bottom edge"),
            ([-1, 0, 5, 5], "starts outside the frame"),
            ([0, 0, 0, 5], "zero width"),
            ([0, 0, 5, 0], "zero height"),
        ],
    )
    def test_an_unusable_box_is_dropped_not_clamped(
        self, tmp_path: Path, bbox: list[float], why: str
    ) -> None:
        payload = _coco(
            categories=[{"id": 1, "name": "dog"}],
            images=[{"id": 0, "file_name": "a.jpg", "width": 40, "height": 30}],
            annotations=[{"id": 1, "image_id": 0, "category_id": 1, "bbox": bbox}],
        )
        split = load_split(_write_split(tmp_path / "train", payload))
        assert split.annotations[0].boxes == [], why
        assert split.skipped_boxes == 1

    def test_a_missing_image_file_is_skipped_and_counted(self, tmp_path: Path) -> None:
        path = _write_split(tmp_path / "train", _PLACEHOLDER_STYLE, make_images=False)
        split = load_split(path)
        assert split.annotations == ()
        assert split.skipped_images == 1

    def test_an_image_with_no_annotations_is_kept(self, tmp_path: Path) -> None:
        # A pure-background image is real supervision for a detector — `samples_for_task`
        # keeps it deliberately, so dropping it here would quietly change the dataset.
        payload = _coco(
            categories=[{"id": 1, "name": "dog"}],
            images=[{"id": 0, "file_name": "empty.jpg", "width": 40, "height": 30}],
            annotations=[],
        )
        split = load_split(_write_split(tmp_path / "train", payload))
        assert len(split.annotations) == 1
        assert split.annotations[0].boxes == []


class TestUntrustedInput:
    def test_a_traversing_file_name_is_refused(self, tmp_path: Path) -> None:
        secret = tmp_path / "secret.jpg"
        _write_image(secret)
        payload = _coco(
            categories=[{"id": 1, "name": "dog"}],
            images=[{"id": 0, "file_name": "../secret.jpg", "width": 40, "height": 30}],
            annotations=[],
        )
        split = load_split(_write_split(tmp_path / "train", payload, make_images=False))
        assert split.annotations == ()
        assert split.skipped_images == 1

    def test_malformed_json_raises_value_error(self, tmp_path: Path) -> None:
        (tmp_path / "train").mkdir()
        (tmp_path / "train" / COCO_FILENAME).write_text("{ not json")
        with pytest.raises(ValueError, match="not valid JSON"):
            load_split(tmp_path / "train" / COCO_FILENAME)

    @pytest.mark.parametrize("missing", ["images", "annotations", "categories"])
    def test_a_missing_top_level_list_raises_value_error(
        self, tmp_path: Path, missing: str
    ) -> None:
        payload = dict(_PLACEHOLDER_STYLE)
        del payload[missing]
        (tmp_path / "train").mkdir()
        (tmp_path / "train" / COCO_FILENAME).write_text(json.dumps(payload))
        with pytest.raises(ValueError):
            load_split(tmp_path / "train" / COCO_FILENAME)


class TestFindingTheAnnotationFiles:
    def test_a_split_directory_per_child_is_found(self, tmp_path: Path) -> None:
        for split in ("train", "valid", "test"):
            _write_split(tmp_path / split, _PLACEHOLDER_STYLE)
        assert [p.parent.name for p in find_coco_files(tmp_path)] == ["test", "train", "valid"]

    def test_an_annotation_file_in_the_root_is_found(self, tmp_path: Path) -> None:
        _write_split(tmp_path, _PLACEHOLDER_STYLE)
        assert find_coco_files(tmp_path) == [tmp_path / COCO_FILENAME]

    def test_the_scan_does_not_recurse_past_one_level(self, tmp_path: Path) -> None:
        # Bounded for the same reason `list_images` is: pointing this at `/` must not
        # walk the user's entire disk.
        _write_split(tmp_path / "a" / "b", _PLACEHOLDER_STYLE)
        assert find_coco_files(tmp_path) == []

    def test_a_path_that_is_not_a_folder_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Not a folder"):
            find_coco_files(tmp_path / "nope")


class TestImportingIntoTheStore:
    @pytest.fixture(autouse=True)
    def _data_root(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        from app.core.config import get_settings
        from app.datasets.db import reset_connection

        monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
        get_settings.cache_clear()
        reset_connection()

    def test_every_split_lands_in_one_dataset(self, tmp_path: Path) -> None:
        _write_split(tmp_path / "export" / "train", _PLACEHOLDER_STYLE)
        _write_split(tmp_path / "export" / "valid", _ZERO_IS_REAL_STYLE)

        store = DatasetStore()
        dataset_id, summary = import_coco_dataset(store, "Mixed", tmp_path / "export")

        assert summary.images == 2
        assert summary.boxes == 4
        assert summary.class_names == ("dog", "person", "platelets", "rbc")
        assert summary.sources == ("train", "valid")
        assert store.counts(dataset_id).boxes == 4

    def test_the_stored_boxes_carry_the_imported_provenance(self, tmp_path: Path) -> None:
        _write_split(tmp_path / "export" / "train", _PLACEHOLDER_STYLE)
        store = DatasetStore()
        dataset_id, _ = import_coco_dataset(store, "Thermal", tmp_path / "export")

        _, _, _, _, boxes = store.image_annotations(dataset_id)[0]
        assert {box.provenance for box in boxes} == {"imported"}
        assert {box.prompt for box in boxes} == {"dog", "person"}

    def test_a_directory_with_no_annotation_file_is_rejected(self, tmp_path: Path) -> None:
        (tmp_path / "empty").mkdir()
        with pytest.raises(ValueError, match=COCO_FILENAME):
            import_coco_dataset(DatasetStore(), "Nothing", tmp_path / "empty")

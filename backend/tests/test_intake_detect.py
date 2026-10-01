"""Doc 136: what a folder or video holds, per format, before anything is imported."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.datasets.intake import walk as walk_module
from app.datasets.intake.detect import scan
from app.datasets.intake.segmentation import decompress_counts, mask_rle
from tests import intake_fixtures as fx


def test_coco_splits_classes_types_and_the_picture_in_no_file(tmp_path: Path) -> None:
    detection, documents, _ = scan(fx.coco(tmp_path / "set"))
    assert detection.kind == "coco"
    assert detection.splits == ["train", "val"]  # "valid" normalised, as doc 31 does
    assert detection.annotation_files == 2 and len(documents) == 2
    assert detection.annotated_pictures == 3 and detection.pictures == 4
    assert detection.objects == 3
    # The unused placeholder category ("Signals", id 0) is not a class (doc 31).
    assert detection.classes == ["person", "signal"]
    assert detection.annotation_types == ["boxes", "masks"]
    assert detection.convention == "xywh"
    assert any("in no annotation file" in note for note in detection.notes)


def test_yolo_names_from_data_yaml_and_polygons_as_masks(tmp_path: Path) -> None:
    detection, _, _ = scan(fx.yolo(tmp_path / "y"))
    assert detection.kind == "yolo"
    assert detection.classes == ["car", "person"]
    assert detection.annotation_types == ["boxes", "masks"]
    assert detection.pictures == 3 and detection.annotated_pictures == 3  # c.jpg: background
    assert detection.splits == ["train"]


def test_pascal_voc(tmp_path: Path) -> None:
    detection, documents, _ = scan(fx.voc(tmp_path / "v"))
    assert detection.kind == "voc" and detection.classes == ["dog"]
    assert documents[0].payload["annotations"][0]["bbox"] == [5.0, 6.0, 20.0, 24.0]


def test_openlabel_per_camera_without_track_and_with_sizes(tmp_path: Path) -> None:
    detection, documents, _ = scan(fx.openlabel(tmp_path / "o"))
    assert detection.kind == "openlabel"
    assert detection.classes == ["person"]
    assert detection.annotated_pictures == 2
    # The sizes the converter leaves out are read from the pictures (found 2026-10-01).
    assert all(image["width"] == fx.W for image in documents[0].payload["images"])


def test_pictures_only_and_a_video(tmp_path: Path) -> None:
    pictures, _, _ = scan(fx.pictures_only(tmp_path / "p"))
    assert pictures.kind == "images" and pictures.pictures == 3 and pictures.annotated_pictures == 0
    video, _, _ = scan(fx.video(tmp_path / "clip.mp4"))
    assert video.kind == "video" and video.videos == 1 and video.name == "clip"


def test_an_empty_folder_says_what_was_expected(tmp_path: Path) -> None:
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValueError, match="COCO, YOLO, Pascal VOC or OpenLABEL"):
        scan(tmp_path / "empty")


def test_a_huge_folder_is_refused_not_walked(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(walk_module, "MAX_FILES", 2)
    with pytest.raises(ValueError, match="choose the dataset's own folder"):
        scan(fx.pictures_only(tmp_path / "p"))


def test_compressed_rle_round_trips_against_pycocotools_encoder() -> None:
    for counts in ([5, 2, 2, 3], [0, 12], fx.square_counts(), [1, 40, 3, 900, 2]):
        assert decompress_counts(fx.compress(counts)) == counts
    rle = mask_rle({"size": [3, 4], "counts": fx.compress([5, 2, 2, 3])}, width=4, height=3)
    assert rle is not None and rle.counts == [5, 2, 2, 3]


def test_a_mask_of_another_size_is_refused() -> None:
    assert mask_rle({"size": [3, 4], "counts": [12]}, width=8, height=8) is None

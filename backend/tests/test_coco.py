"""Tests for the COCO export.

The load-bearing rule: annotations are positive boxes only. A COCO annotation means
"an object is here"; exporting a negative would teach a consumer the opposite.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.datasets.coco import COCO_FILENAME, build_coco, write_coco
from app.datasets.models import Box


def box(label: str, **kwargs: float) -> Box:
    defaults = {"x": 10.0, "y": 20.0, "w": 30.0, "h": 40.0}
    defaults.update(kwargs)
    return Box(label=label, provenance="hand-drawn", **defaults)


def images(*boxes: Box) -> list[tuple[int, str, int, int, list[Box]]]:
    return [(1, "/images/a.jpg", 640, 480, list(boxes))]


class TestBuildCoco:
    def test_has_the_required_top_level_keys(self) -> None:
        coco = build_coco("Cats", images(box("positive")))
        assert {"info", "licenses", "images", "annotations", "categories"} <= set(coco)

    def test_exports_positive_boxes(self) -> None:
        coco = build_coco("Cats", images(box("positive")))
        assert len(coco["annotations"]) == 1

    def test_excludes_negative_and_unclear(self) -> None:
        coco = build_coco("Cats", images(box("positive"), box("negative"), box("unclear")))
        assert len(coco["annotations"]) == 1

    def test_exports_nothing_when_there_are_no_positives(self) -> None:
        coco = build_coco("Cats", images(box("negative"), box("unclear")))
        assert coco["annotations"] == []

    def test_images_are_listed_even_without_annotations(self) -> None:
        """A reviewed image with no objects is a real negative example, not an absence."""
        coco = build_coco("Cats", images(box("negative")))
        assert len(coco["images"]) == 1

    def test_bbox_is_xywh_top_left(self) -> None:
        coco = build_coco("Cats", images(box("positive", x=5, y=6, w=7, h=8)))
        assert coco["annotations"][0]["bbox"] == [5, 6, 7, 8]

    def test_area_is_width_times_height(self) -> None:
        coco = build_coco("Cats", images(box("positive", w=7, h=8)))
        assert coco["annotations"][0]["area"] == 56

    def test_annotation_ids_are_unique_and_sequential(self) -> None:
        coco = build_coco("Cats", images(box("positive"), box("positive"), box("positive")))
        assert [a["id"] for a in coco["annotations"]] == [1, 2, 3]

    def test_annotations_reference_their_image(self) -> None:
        coco = build_coco("Cats", images(box("positive")))
        assert coco["annotations"][0]["image_id"] == coco["images"][0]["id"]

    def test_image_carries_dimensions_and_filename(self) -> None:
        entry = build_coco("Cats", images(box("positive")))["images"][0]
        assert (entry["width"], entry["height"]) == (640, 480)
        assert entry["file_name"] == "a.jpg"

    def test_score_is_carried_when_present(self) -> None:
        scored = Box(label="positive", provenance="grounding-dino", x=0, y=0, w=1, h=1, score=0.9)
        coco = build_coco("Cats", images(scored))
        assert coco["annotations"][0]["score"] == 0.9

    def test_score_is_omitted_when_absent(self) -> None:
        coco = build_coco("Cats", images(box("positive")))
        assert "score" not in coco["annotations"][0]

    def test_prompt_is_recorded_in_info(self) -> None:
        coco = build_coco("Cats", images(box("positive")), prompt="a cat")
        assert coco["info"]["prompt"] == "a cat"

    def test_single_category_in_wave_one(self) -> None:
        coco = build_coco("Cats", images(box("positive")))
        assert len(coco["categories"]) == 1
        assert coco["annotations"][0]["category_id"] == coco["categories"][0]["id"]


class TestWriteCoco:
    def test_writes_valid_json_to_the_expected_name(self, tmp_path: Path) -> None:
        path = write_coco(tmp_path, build_coco("Cats", images(box("positive"))))

        assert path.name == COCO_FILENAME
        assert json.loads(path.read_text())["annotations"][0]["bbox"] == [10, 20, 30, 40]

    def test_creates_the_directory_if_absent(self, tmp_path: Path) -> None:
        path = write_coco(tmp_path / "nested" / "deeper", build_coco("Cats", images()))
        assert path.is_file()

    def test_overwrites_a_previous_export(self, tmp_path: Path) -> None:
        write_coco(tmp_path, build_coco("Cats", images(box("positive"), box("positive"))))
        write_coco(tmp_path, build_coco("Cats", images(box("positive"))))

        written = json.loads((tmp_path / COCO_FILENAME).read_text())
        assert len(written["annotations"]) == 1

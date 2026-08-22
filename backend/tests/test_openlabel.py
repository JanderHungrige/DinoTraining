"""ASAM OpenLABEL -> COCO (doc 49).

Three rules are the whole module, and each one produces a plausible-looking dataset when it
goes the other way — no exception, no empty result, just a detector that learns the wrong
thing. So each gets tests from the direction that would be wrong.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.datasets.openlabel import camera_names, load_openlabel
from app.datasets.openlabel_to_coco import convert, write_coco


def openlabel(frames: dict[str, Any], objects: dict[str, Any]) -> dict[str, Any]:
    return {
        "streams": {
            "rgb_center": {"type": "camera"},
            "rgb_left": {"type": "camera"},
            "lidar": {"type": "lidar"},
        },
        "objects": objects,
        "frames": frames,
    }


def frame(image: str, objects: dict[str, Any], camera: str = "rgb_center") -> dict[str, Any]:
    return {
        "frame_properties": {"streams": {camera: {"uri": f"/{camera}/{image}"}}},
        "objects": objects,
    }


def bbox(val: list[float], camera: str = "rgb_center") -> dict[str, Any]:
    return {"object_data": {"bbox": [{"val": val, "coordinate_system": camera}]}}


def poly(val: list[float], *, closed: bool, camera: str = "rgb_center") -> dict[str, Any]:
    return {
        "object_data": {
            "poly2d": [{"val": val, "closed": closed, "coordinate_system": camera}]
        }
    }


class TestOneCameraAtATime:
    """The same physical object is annotated separately in every sensor that sees it.

    Ignoring `coordinate_system` would multiply every object by the sensor count and pair
    one camera's boxes with another camera's images — a dataset that trains, and teaches
    nothing.
    """

    def _both(self) -> dict[str, Any]:
        return openlabel(
            {
                "0": {
                    "frame_properties": {
                        "streams": {
                            "rgb_center": {"uri": "/rgb_center/a.png"},
                            "rgb_left": {"uri": "/rgb_left/a.png"},
                        }
                    },
                    "objects": {
                        "o1": {
                            "object_data": {
                                "bbox": [
                                    {"val": [100, 100, 20, 40], "coordinate_system": "rgb_center"},
                                    {"val": [700, 100, 20, 40], "coordinate_system": "rgb_left"},
                                ]
                            }
                        }
                    },
                }
            },
            {"o1": {"type": "person"}},
        )

    def test_only_the_named_camera_contributes_boxes(self) -> None:
        document, summary = convert(self._both(), "rgb_center")
        assert len(document["annotations"]) == 1
        assert summary.skipped_other_sensors == 1

    def test_the_box_is_that_camera_s_own(self) -> None:
        # The decisive check: taking the wrong sensor's box gives a box in the right place
        # for a *different* image, which nothing downstream can detect.
        document, _ = convert(self._both(), "rgb_left")
        assert document["annotations"][0]["bbox"][0] == pytest.approx(690.0)

    def test_the_image_is_that_camera_s_own(self) -> None:
        document, _ = convert(self._both(), "rgb_left")
        assert document["images"][0]["file_name"] == "rgb_left/a.png"

    def test_a_frame_without_this_camera_is_skipped_not_failed(self) -> None:
        # Sensors are not all sampled at the same rate; a gap is normal.
        source = openlabel(
            {"0": frame("a.png", {}, camera="rgb_left")}, {}
        )
        document, _ = convert(source, "rgb_center")
        assert document["images"] == []


class TestTheBoxConvention:
    """OpenLABEL is `[cx, cy, w, h]`; COCO is `[x, y, w, h]` from the top-left.

    Missing this shifts every box by half its own size — small enough to read as ordinary
    annotation noise rather than as a bug.
    """

    def _one(self, val: list[float]) -> list[float]:
        source = openlabel(
            {"0": frame("a.png", {"o1": bbox(val)})}, {"o1": {"type": "person"}}
        )
        document, _ = convert(source, "rgb_center")
        result = document["annotations"][0]["bbox"]
        assert isinstance(result, list)
        return [float(v) for v in result]

    def test_a_centre_becomes_a_corner(self) -> None:
        assert self._one([100.0, 200.0, 20.0, 40.0]) == pytest.approx([90.0, 180.0, 20.0, 40.0])

    def test_it_is_not_passed_through_unchanged(self) -> None:
        assert self._one([100.0, 200.0, 20.0, 40.0])[0] != pytest.approx(100.0)

    def test_the_size_is_untouched(self) -> None:
        assert self._one([100.0, 200.0, 20.0, 40.0])[2:] == pytest.approx([20.0, 40.0])

    def test_a_malformed_val_is_dropped_rather_than_guessed(self) -> None:
        source = openlabel(
            {"0": frame("a.png", {"o1": bbox([1.0, 2.0])})}, {"o1": {"type": "person"}}
        )
        document, _ = convert(source, "rgb_center")
        assert document["annotations"] == []


class TestClosedPolygonsOnly:
    """A closed quad round a signal has a meaningful extent. An open polyline along a rail
    track has one that is mostly ballast and vegetation."""

    def _convert(self, shape: dict[str, Any], type_name: str = "signal") -> Any:
        source = openlabel(
            {"0": frame("a.png", {"o1": shape})}, {"o1": {"type": type_name}}
        )
        return convert(source, "rgb_center")

    def test_a_closed_polygon_becomes_its_extent(self) -> None:
        document, _ = self._convert(poly([10, 20, 30, 20, 30, 60, 10, 60], closed=True))
        assert document["annotations"][0]["bbox"] == pytest.approx([10.0, 20.0, 20.0, 40.0])

    def test_an_open_polyline_is_refused(self) -> None:
        document, summary = self._convert(
            poly([0, 0, 500, 300, 1000, 700], closed=False), "track"
        )
        assert document["annotations"] == []
        assert summary.skipped_open_polylines == 1

    def test_the_refusal_is_counted_rather_than_silent(self) -> None:
        _, summary = self._convert(poly([0, 0, 9, 9, 4, 4], closed=False), "track")
        assert summary.skipped_open_polylines == 1


class TestExclusionAndSize:
    def test_an_excluded_type_contributes_nothing(self) -> None:
        source = openlabel(
            {"0": frame("a.png", {"o1": bbox([100, 100, 40, 40])})}, {"o1": {"type": "track"}}
        )
        document, summary = convert(source, "rgb_center", exclude=frozenset({"track"}))
        assert document["annotations"] == []
        assert summary.excluded_classes == ("track",)

    def test_a_tiny_box_is_dropped_and_counted(self) -> None:
        # A 2 px annotation carries no appearance to learn from and still costs a detector
        # a false negative it can never avoid.
        source = openlabel(
            {"0": frame("a.png", {"o1": bbox([100, 100, 2, 30])})}, {"o1": {"type": "person"}}
        )
        document, summary = convert(source, "rgb_center")
        assert document["annotations"] == []
        assert summary.skipped_tiny == 1

    def test_the_threshold_is_configurable(self) -> None:
        source = openlabel(
            {"0": frame("a.png", {"o1": bbox([100, 100, 2, 30])})}, {"o1": {"type": "person"}}
        )
        document, _ = convert(source, "rgb_center", min_pixels=1.0)
        assert len(document["annotations"]) == 1


class TestTheCocoDocument:
    def _document(self) -> dict[str, Any]:
        source = openlabel(
            {
                "1": frame("b.png", {"o2": bbox([50, 50, 30, 30])}),
                "0": frame("a.png", {"o1": bbox([100, 100, 20, 40])}),
            },
            {"o1": {"type": "person"}, "o2": {"type": "signal_pole"}},
        )
        document, _ = convert(source, "rgb_center")
        return document

    def test_frames_are_ordered_numerically_not_lexically(self) -> None:
        # '10' sorts before '2' as a string, which would scramble a 98-frame sequence.
        source = openlabel(
            {str(i): frame(f"{i}.png", {}) for i in (0, 2, 10)}, {}
        )
        document, _ = convert(source, "rgb_center")
        assert [i["file_name"] for i in document["images"]] == [
            "rgb_center/0.png",
            "rgb_center/2.png",
            "rgb_center/10.png",
        ]

    def test_the_leading_slash_is_stripped(self) -> None:
        # The importer resolves file names relative to the annotation file; an absolute
        # path would escape the dataset folder.
        assert not self._document()["images"][0]["file_name"].startswith("/")

    def test_categories_are_named_and_numbered_from_one(self) -> None:
        categories = self._document()["categories"]
        assert [c["id"] for c in categories] == [1, 2]
        assert {c["name"] for c in categories} == {"person", "signal_pole"}

    def test_each_annotation_points_at_a_real_image(self) -> None:
        document = self._document()
        ids = {image["id"] for image in document["images"]}
        assert all(a["image_id"] in ids for a in document["annotations"])

    def test_it_writes_where_the_importer_looks(self, tmp_path: Path) -> None:
        target = write_coco(self._document(), tmp_path / "train")
        assert target.name == "_annotations.coco.json"
        assert json.loads(target.read_text())["images"]


class TestReadingTheFile:
    def test_it_lists_cameras_and_not_the_lidar(self) -> None:
        assert camera_names(openlabel({}, {})) == ("rgb_center", "rgb_left")

    def test_a_non_openlabel_file_says_so(self, tmp_path: Path) -> None:
        path = tmp_path / "x.json"
        path.write_text('{"images": [], "annotations": []}')
        with pytest.raises(ValueError, match="OpenLABEL"):
            load_openlabel(path)

    def test_broken_json_says_so(self, tmp_path: Path) -> None:
        path = tmp_path / "x.json"
        path.write_text("{ not json")
        with pytest.raises(ValueError, match="valid JSON"):
            load_openlabel(path)

    def test_a_file_without_frames_is_refused(self, tmp_path: Path) -> None:
        path = tmp_path / "x.json"
        path.write_text('{"openlabel": {"objects": {}}}')
        with pytest.raises(ValueError, match="frames"):
            load_openlabel(path)

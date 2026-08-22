"""Cutting frames into tiles (doc 49).

Two rules carry the risk, and both fail by producing *more* data rather than less — which
looks like success. Centre-assignment stops one object becoming four; keeping empty tiles
stops the detector learning that every image contains something.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.datasets.tiling import plan_tiles, retile
from app.datasets.tiling_images import write_tiles


def document(boxes: list[list[float]], images: int = 1) -> dict[str, Any]:
    return {
        "info": {},
        "images": [{"id": i + 1, "file_name": f"rgb/{i}.png"} for i in range(images)],
        "annotations": [
            {"id": j + 1, "image_id": 1, "category_id": 1, "bbox": b, "area": b[2] * b[3]}
            for j, b in enumerate(boxes)
        ],
        "categories": [{"id": 1, "name": "person"}],
    }


class TestThePlan:
    def test_a_grid_has_one_tile_per_cell(self) -> None:
        assert len(plan_tiles(2464, 1600, 4, 3)) == 12

    def test_tiles_overlap_so_a_seam_object_lands_whole_somewhere(self) -> None:
        tiles = plan_tiles(1000, 100, 2, 1, overlap=0.2)
        first, second = tiles[0], tiles[1]
        assert first.x + first.width > second.x

    def test_the_last_tile_ends_at_the_frame_edge(self) -> None:
        # Off by a few pixels here leaves a strip that no tile covers, and every object in
        # it silently disappears.
        tiles = plan_tiles(2464, 1600, 4, 3)
        assert max(t.x + t.width for t in tiles) == 2464
        assert max(t.y + t.height for t in tiles) == 1600

    def test_a_one_by_one_grid_is_the_whole_frame(self) -> None:
        tile = plan_tiles(800, 600, 1, 1)[0]
        assert (tile.x, tile.y, tile.width, tile.height) == (0, 0, 800, 600)

    def test_a_degenerate_grid_is_refused(self) -> None:
        with pytest.raises(ValueError, match="1x1"):
            plan_tiles(100, 100, 0, 3)

    def test_an_impossible_overlap_is_refused(self) -> None:
        with pytest.raises(ValueError, match="overlap"):
            plan_tiles(100, 100, 2, 2, overlap=1.0)


class TestOneObjectStaysOneObject:
    """With overlapping tiles, an any-overlap rule duplicates every object near a seam and
    inflates every downstream count — including the metrics that report success."""

    def test_a_box_lands_in_exactly_one_tile(self) -> None:
        # Placed deliberately in the shared strip between two tiles.
        tiles = plan_tiles(1000, 100, 2, 1, overlap=0.2)
        seam = tiles[1].x + 2
        tiled, summary = retile(document([[float(seam), 10.0, 8.0, 8.0]]), 1000, 100, 2, 1, 0.2)
        assert summary.boxes == 1
        assert len(tiled["annotations"]) == 1

    def test_it_is_the_tile_holding_the_centre(self) -> None:
        tiled, _ = retile(document([[900.0, 10.0, 10.0, 10.0]]), 1000, 100, 2, 1)
        placed = tiled["annotations"][0]
        holder = next(i for i in tiled["images"] if i["id"] == placed["image_id"])
        assert "r0c1" in holder["file_name"]

    def test_coordinates_become_tile_local(self) -> None:
        # A box left in frame coordinates would sit outside its own tile — and would train
        # without complaint, because nothing checks.
        tiled, _ = retile(document([[900.0, 10.0, 10.0, 10.0]]), 1000, 100, 2, 1, overlap=0.0)
        x, y, w, h = tiled["annotations"][0]["bbox"]
        assert x == pytest.approx(400.0)
        assert (y, w, h) == pytest.approx((10.0, 10.0, 10.0))

    def test_a_box_is_clipped_to_its_tile(self) -> None:
        # Centre at 495 puts it in tile 0 (0..500); the box runs to 505 and must be cut.
        tiled, _ = retile(document([[485.0, 10.0, 20.0, 10.0]]), 1000, 100, 2, 1, overlap=0.0)
        _, _, w, _ = tiled["annotations"][0]["bbox"]
        assert w == pytest.approx(15.0)

    def test_the_nearest_tile_wins_when_two_contain_the_centre(self) -> None:
        # Tiles 0..600 and 400..1000: a centre at 420 is inside both. Tile 0's centre is
        # 300 and tile 1's is 700, so tile 0 is nearer and takes it.
        tiled, _ = retile(document([[416.0, 10.0, 8.0, 8.0]]), 1000, 100, 2, 1, 0.2)
        placed = tiled["annotations"][0]
        holder = next(i for i in tiled["images"] if i["id"] == placed["image_id"])
        assert "r0c0" in holder["file_name"]


class TestBackgroundTiles:
    """Sky and ballast are the background this detector must learn to reject, so dropping
    empties teaches it that every image contains something. Keeping all of them is the
    opposite mistake — a fixed camera makes the grid overwhelmingly background, and
    predicting nothing then scores well."""

    def test_empty_tiles_are_kept_up_to_the_ratio(self) -> None:
        tiled, summary = retile(
            document([[10.0, 10.0, 20.0, 20.0]]), 1000, 100, 4, 1, background_ratio=1.0
        )
        assert summary.empty_tiles == 1
        assert len(tiled["images"]) == 2

    def test_a_higher_ratio_keeps_more(self) -> None:
        tiled, _ = retile(
            document([[10.0, 10.0, 20.0, 20.0]]), 1000, 100, 4, 1, background_ratio=3.0
        )
        assert len(tiled["images"]) == 4

    def test_a_ratio_of_zero_keeps_only_tiles_with_boxes(self) -> None:
        tiled, summary = retile(
            document([[10.0, 10.0, 20.0, 20.0]]), 1000, 100, 4, 1, background_ratio=0.0
        )
        assert summary.empty_tiles == 0
        assert len(tiled["images"]) == 1

    def test_no_box_survives_the_cap(self) -> None:
        # Capping background must never cost a positive.
        boxes = [[10.0, 10.0, 20.0, 20.0], [900.0, 10.0, 20.0, 20.0]]
        _, summary = retile(document(boxes), 1000, 100, 4, 1, background_ratio=0.0)
        assert summary.boxes == 2

    def test_a_document_with_no_boxes_keeps_the_whole_grid(self) -> None:
        # An unlabelled folder being prepared for annotation is a legitimate input, and
        # there is no imbalance to correct. Returning nothing would be a silent total loss.
        tiled, summary = retile(document([], images=3), 1000, 100, 2, 2)
        assert summary.tiles_per_frame == 4
        assert len(tiled["images"]) == 12


class TestTheDocumentStaysValid:
    def test_ids_are_renumbered_from_one(self) -> None:
        tiled, _ = retile(document([[10.0, 10.0, 20.0, 20.0]]), 1000, 100, 2, 1)
        assert [i["id"] for i in tiled["images"]] == [1, 2]
        assert tiled["annotations"][0]["id"] == 1

    def test_every_annotation_points_at_a_real_tile(self) -> None:
        tiled, _ = retile(
            document([[10.0, 10.0, 20.0, 20.0], [900.0, 10.0, 10.0, 10.0]]), 1000, 100, 2, 1
        )
        ids = {i["id"] for i in tiled["images"]}
        assert all(a["image_id"] in ids for a in tiled["annotations"])

    def test_tiles_carry_their_own_size(self) -> None:
        tiled, _ = retile(document([]), 1000, 100, 2, 1, overlap=0.0)
        assert tiled["images"][0]["width"] == 500

    def test_categories_survive(self) -> None:
        tiled, _ = retile(document([[10.0, 10.0, 20.0, 20.0]]), 1000, 100, 2, 1)
        assert tiled["categories"] == [{"id": 1, "name": "person"}]

    def test_the_file_name_says_which_tile(self) -> None:
        tiled, _ = retile(document([]), 1000, 100, 2, 2)
        names = [i["file_name"] for i in tiled["images"]]
        assert "rgb/0_r0c0.png" in names
        assert "rgb/0_r1c1.png" in names


class TestCuttingTheImages:
    """The document and the files must agree. A retiled document pointing at whole frames
    trains on full images with tile-local boxes — every box in the wrong place, and nothing
    raises."""

    def _frame(self, directory: Path, name: str = "rgb/0.png") -> Path:
        from PIL import Image

        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (1000, 100), (30, 60, 90)).save(path)
        return path

    def test_it_writes_one_file_per_tile(self, tmp_path: Path) -> None:
        source, target = tmp_path / "in", tmp_path / "out"
        self._frame(source)
        tiled, _ = retile(document([]), 1000, 100, 2, 1, overlap=0.0)
        assert write_tiles(tiled, source, target, 2, 1, overlap=0.0) == 2

    def test_it_writes_only_the_tiles_the_document_names(self, tmp_path: Path) -> None:
        # `retile` caps empty tiles; cutting the whole grid anyway would leave files on
        # disk that the dataset does not refer to, for the next glob to pick up.
        source, target = tmp_path / "in", tmp_path / "out"
        self._frame(source)
        tiled, _ = retile(
            document([[10.0, 10.0, 20.0, 20.0]]), 1000, 100, 4, 1,
            overlap=0.0, background_ratio=0.0,
        )
        assert len(tiled["images"]) == 1
        assert write_tiles(tiled, source, target, 4, 1, overlap=0.0) == 1
        assert len(list(target.rglob("*.png"))) == 1

    def test_every_file_the_document_names_exists(self, tmp_path: Path) -> None:
        source, target = tmp_path / "in", tmp_path / "out"
        self._frame(source)
        tiled, _ = retile(document([]), 1000, 100, 2, 2, overlap=0.0)
        write_tiles(tiled, source, target, 2, 2, overlap=0.0)
        assert all((target / i["file_name"]).is_file() for i in tiled["images"])

    def test_a_tile_has_the_size_the_document_claims(self, tmp_path: Path) -> None:
        from PIL import Image

        source, target = tmp_path / "in", tmp_path / "out"
        self._frame(source)
        tiled, _ = retile(document([]), 1000, 100, 2, 1, overlap=0.0)
        write_tiles(tiled, source, target, 2, 1, overlap=0.0)
        entry = tiled["images"][0]
        with Image.open(target / entry["file_name"]) as opened:
            assert opened.size == (entry["width"], entry["height"])

    def test_a_missing_frame_is_skipped_rather_than_fatal(self, tmp_path: Path) -> None:
        # One unreadable frame in ninety-eight must not lose the other ninety-seven.
        tiled, _ = retile(document([]), 1000, 100, 2, 1)
        assert write_tiles(tiled, tmp_path / "in", tmp_path / "out", 2, 1) == 0

    def test_each_frame_is_decoded_once(self, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        from PIL import Image

        source, target = tmp_path / "in", tmp_path / "out"
        self._frame(source)
        opens = 0
        real = Image.open

        def counting(*args: object, **kwargs: object) -> object:
            nonlocal opens
            opens += 1
            return real(*args, **kwargs)  # type: ignore[arg-type]

        monkeypatch.setattr("app.datasets.tiling_images.Image.open", counting)
        tiled, _ = retile(document([]), 1000, 100, 4, 3)
        write_tiles(tiled, source, target, 4, 3)
        assert opens == 1

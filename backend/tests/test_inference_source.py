"""Tests for resolving what the user pointed the viewer at.

The contract under test is not "list a folder" — Wave 1 already does that — it is that a
single file and a folder come back as *the same shape*, under an identity that is not a
path. Feature 19's viewer and a future video source both key on that identity, so a
regression here is invisible until something else stops working.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.ml.images import ImageReadError
from app.ml.inference.source import MAX_ITEMS, resolve_source


def write_image(path: Path, fmt: str = "PNG") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (32, 24), (10, 90, 60)).save(path, format=fmt)
    return path


class TestSingleFile:
    def test_a_file_resolves_to_one_item(self, tmp_path: Path) -> None:
        target = write_image(tmp_path / "cat.png")

        source = resolve_source(str(target))

        assert source.kind == "file"
        assert source.root == target
        assert len(source.items) == 1
        assert source.items[0].name == "cat.png"
        assert source.items[0].path == target

    def test_a_non_image_file_is_rejected(self, tmp_path: Path) -> None:
        notes = tmp_path / "notes.txt"
        notes.write_text("not an image")

        with pytest.raises(ImageReadError):
            resolve_source(str(notes))

    def test_a_missing_path_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            resolve_source(str(tmp_path / "nope.png"))

    def test_the_path_is_resolved_to_an_absolute(self, tmp_path: Path) -> None:
        write_image(tmp_path / "sub" / "a.png")

        source = resolve_source(str(tmp_path / "sub" / ".." / "sub" / "a.png"))

        assert source.items[0].path.is_absolute()
        assert ".." not in source.items[0].path.parts


class TestFolder:
    def test_a_folder_resolves_to_its_images_in_order(self, tmp_path: Path) -> None:
        write_image(tmp_path / "b.png")
        write_image(tmp_path / "a.jpg", fmt="JPEG")
        (tmp_path / "readme.txt").write_text("ignored")

        source = resolve_source(str(tmp_path))

        assert source.kind == "folder"
        assert [item.name for item in source.items] == ["a.jpg", "b.png"]
        assert source.truncated is False

    def test_an_empty_folder_is_not_an_error(self, tmp_path: Path) -> None:
        # "No images here" is something the viewer must be able to say, not a failure.
        source = resolve_source(str(tmp_path))

        assert source.items == ()
        assert source.kind == "folder"

    def test_listing_does_not_open_the_files(self, tmp_path: Path) -> None:
        # A truncated file in a photo folder must not break picking the folder; it fails
        # when it is selected, which is where the user can act on it.
        (tmp_path / "broken.png").write_bytes(b"not really a png")

        source = resolve_source(str(tmp_path))

        assert [item.name for item in source.items] == ["broken.png"]

    def test_more_than_max_items_is_truncated_and_says_so(self, tmp_path: Path) -> None:
        for index in range(MAX_ITEMS + 3):
            write_image(tmp_path / f"{index:05d}.png")

        source = resolve_source(str(tmp_path))

        assert len(source.items) == MAX_ITEMS
        assert source.truncated is True


class TestItemIdentity:
    def test_item_id_is_stable_across_calls(self, tmp_path: Path) -> None:
        write_image(tmp_path / "a.png")

        first = resolve_source(str(tmp_path)).items[0].item_id
        second = resolve_source(str(tmp_path)).items[0].item_id

        assert first == second

    def test_item_id_differs_per_file(self, tmp_path: Path) -> None:
        write_image(tmp_path / "a.png")
        write_image(tmp_path / "b.png")

        ids = {item.item_id for item in resolve_source(str(tmp_path)).items}

        assert len(ids) == 2

    def test_item_id_is_not_a_path(self, tmp_path: Path) -> None:
        # The whole point: consumers keyed on item_id keep working when items stop
        # being files. A path-shaped id would let "an item is a file" leak into them.
        item = resolve_source(str(write_image(tmp_path / "a.png"))).items[0]

        assert "/" not in item.item_id
        assert "a.png" not in item.item_id
        assert len(item.item_id) == 16

    def test_the_same_file_reached_two_ways_has_one_id(self, tmp_path: Path) -> None:
        target = write_image(tmp_path / "sub" / "a.png")

        direct = resolve_source(str(target)).items[0].item_id
        indirect = resolve_source(str(tmp_path / "sub")).items[0].item_id

        assert direct == indirect

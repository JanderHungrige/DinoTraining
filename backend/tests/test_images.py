"""Tests for reading user-chosen image files — the app's widest input surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from app.ml.images import FolderNotFoundError, ImageReadError, list_images, read_image


def write_image(path: Path, size: tuple[int, int] = (64, 48), fmt: str = "PNG") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (120, 30, 30)).save(path, format=fmt)
    return path


class TestReadImage:
    def test_reads_a_png(self, tmp_path: Path) -> None:
        image, path = read_image(str(write_image(tmp_path / "a.png")))
        assert (image.width, image.height) == (64, 48)
        assert path.name == "a.png"

    def test_reads_a_jpeg(self, tmp_path: Path) -> None:
        image, _ = read_image(str(write_image(tmp_path / "a.jpg", fmt="JPEG")))
        assert image.width == 64

    def test_converts_to_rgb(self, tmp_path: Path) -> None:
        path = tmp_path / "gray.png"
        Image.new("L", (10, 10), 128).save(path)
        image, _ = read_image(str(path))
        assert image.mode == "RGB"

    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_image(str(tmp_path / "absent.png"))

    def test_a_directory_is_not_an_image(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            read_image(str(tmp_path))

    def test_non_image_file_raises_image_read_error(self, tmp_path: Path) -> None:
        """A stray .txt in a photo folder is expected input, not an internal error."""
        path = tmp_path / "notes.txt"
        path.write_text("definitely not a picture")
        with pytest.raises(ImageReadError):
            read_image(str(path))

    def test_a_text_file_renamed_to_png_is_rejected(self, tmp_path: Path) -> None:
        """The extension is a hint; decoding is the check."""
        path = tmp_path / "fake.png"
        path.write_text("still not a picture")
        with pytest.raises(ImageReadError):
            read_image(str(path))

    def test_truncated_image_is_rejected_cleanly(self, tmp_path: Path) -> None:
        source = write_image(tmp_path / "full.png")
        truncated = tmp_path / "truncated.png"
        truncated.write_bytes(source.read_bytes()[:20])
        with pytest.raises(ImageReadError):
            read_image(str(truncated))

    def test_reading_a_sensitive_file_is_refused(self, tmp_path: Path) -> None:
        """The read surface is narrowed to decodable images, so /etc/hosts is not readable."""
        secret = tmp_path / "secrets.env"
        secret.write_text("HF_TOKEN=hf_supersecret")
        with pytest.raises(ImageReadError):
            read_image(str(secret))


class TestListImages:
    def test_lists_only_images(self, tmp_path: Path) -> None:
        write_image(tmp_path / "a.png")
        write_image(tmp_path / "b.jpg", fmt="JPEG")
        (tmp_path / "notes.txt").write_text("nope")

        found = list_images(str(tmp_path))
        assert [p.name for p in found] == ["a.png", "b.jpg"]

    def test_is_sorted(self, tmp_path: Path) -> None:
        for name in ("c.png", "a.png", "b.png"):
            write_image(tmp_path / name)
        assert [p.name for p in list_images(str(tmp_path))] == ["a.png", "b.png", "c.png"]

    def test_skips_hidden_files(self, tmp_path: Path) -> None:
        write_image(tmp_path / "a.png")
        write_image(tmp_path / ".hidden.png")
        assert [p.name for p in list_images(str(tmp_path))] == ["a.png"]

    def test_is_not_recursive(self, tmp_path: Path) -> None:
        """Pointing this at / must enumerate one level, not walk the whole disk."""
        write_image(tmp_path / "top.png")
        write_image(tmp_path / "nested" / "deep.png")

        assert [p.name for p in list_images(str(tmp_path))] == ["top.png"]

    def test_empty_folder_returns_empty_list(self, tmp_path: Path) -> None:
        assert list_images(str(tmp_path)) == []

    def test_missing_folder_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FolderNotFoundError):
            list_images(str(tmp_path / "absent"))

    def test_a_file_is_not_a_folder(self, tmp_path: Path) -> None:
        path = write_image(tmp_path / "a.png")
        with pytest.raises(FolderNotFoundError):
            list_images(str(path))

"""Doc 138: unpacking a ZIP while it downloads, keeping only what is asked for."""

from __future__ import annotations

import io
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.datasets.examples.zipstream import safe_member, stream_unzip

PNG = bytes(range(256)) * 40
LABELS = b'{"openlabel": {}}' * 50


def archive(entries: dict[str, bytes], stored: frozenset[str] = frozenset()) -> bytes:
    """Written to a seekable buffer, so every local header carries its sizes (as OSDaR23's)."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zipped:
        for name, data in entries.items():
            method = zipfile.ZIP_STORED if name in stored else zipfile.ZIP_DEFLATED
            zipped.writestr(name, data, compress_type=method)
    return buffer.getvalue()


def chunked(data: bytes, size: int) -> Iterator[bytes]:
    for start in range(0, len(data), size):
        yield data[start : start + size]


ENTRIES = {
    "rgb_center/": b"",
    "rgb_center/000.png": PNG,
    "rgb_left/000.png": PNG[::-1],
    "lidar/000.pcd": b"x" * 5000,
    "seq_labels.json": LABELS,
}


def _keep(name: str) -> bool:
    return name.startswith("rgb_center/") or name.endswith("_labels.json")


@pytest.mark.parametrize("chunk", [3, 4096, 1 << 20])
def test_keeps_only_the_wanted_members_whatever_the_chunk_size(tmp_path: Path, chunk: int) -> None:
    data = archive(ENTRIES, stored=frozenset({"rgb_center/000.png"}))
    seen: list[int] = []
    result = stream_unzip(chunked(data, chunk), tmp_path, _keep, lambda done, _n: seen.append(done))
    assert (tmp_path / "rgb_center" / "000.png").read_bytes() == PNG
    assert (tmp_path / "seq_labels.json").read_bytes() == LABELS
    assert sorted(p.name for p in tmp_path.rglob("*") if p.is_file()) == [
        "000.png",
        "seq_labels.json",
    ]
    assert (result.kept, result.skipped) == (2, 2)  # the folder entry is neither
    assert result.kept_bytes == len(PNG) + len(LABELS)
    assert seen == sorted(seen) and result.read_bytes < len(data)  # stops at the directory


def test_an_archive_with_sizes_after_the_data_is_refused() -> None:
    class Unseekable(io.RawIOBase):
        def __init__(self) -> None:
            self.data = bytearray()

        def writable(self) -> bool:
            return True

        def write(self, b: bytes) -> int:  # type: ignore[override]
            self.data += b
            return len(b)

    sink = Unseekable()
    with zipfile.ZipFile(sink, "w", compression=zipfile.ZIP_DEFLATED) as zipped:
        zipped.writestr("rgb_center/000.png", PNG)
    with pytest.raises(ValueError, match="cannot be streamed"):
        stream_unzip([bytes(sink.data)], Path("/nonexistent"), _keep, lambda *_: None)


def test_a_name_leaving_the_folder_is_refused_and_nothing_is_written(tmp_path: Path) -> None:
    dest = tmp_path / "dest"
    with pytest.raises(ValueError, match="outside its folder"):
        stream_unzip([archive({"../evil_labels.json": LABELS})], dest, _keep, lambda *_: None)
    assert not (tmp_path / "evil_labels.json").exists()
    for name in ("/etc/passwd", "a/../../b", "C:/x"):
        with pytest.raises(ValueError):
            safe_member(name)
    assert str(safe_member("rgb_center/000.png")) == "rgb_center/000.png"


def test_a_broken_download_and_a_damaged_member_say_so(tmp_path: Path) -> None:
    data = archive(ENTRIES)
    with pytest.raises(ValueError, match="ended in the middle"):
        stream_unzip([data[: len(data) // 2]], tmp_path / "a", _keep, lambda *_: None)
    stored = bytearray(archive({"seq_labels.json": LABELS}, stored=frozenset({"seq_labels.json"})))
    stored[60] ^= 0xFF  # inside the stored member's data
    with pytest.raises(ValueError, match="damaged"):
        stream_unzip([bytes(stored)], tmp_path / "b", _keep, lambda *_: None)
    with pytest.raises(ValueError, match="not a ZIP"):
        stream_unzip([b"<html>Anubis</html>"], tmp_path / "c", _keep, lambda *_: None)

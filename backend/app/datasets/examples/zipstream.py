"""Unpack a ZIP while it downloads, keeping only the members asked for (doc 138, doc 49).

The archive is read sequentially by its local file headers, so it is never written to
disk and no member is seeked to: each one is decompressed into `dest` or skipped as it
passes. That needs every member's compressed size in its local header, which OSDaR23's
archives have; an archive that defers sizes to a data descriptor is refused, not guessed.
"""

from __future__ import annotations

import logging
import struct
import zlib
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

logger = logging.getLogger(__name__)

_LOCAL = b"PK\x03\x04"
#: The central directory (and everything after it) follows the last member.
_END_MARKERS = (b"PK\x01\x02", b"PK\x05\x06", b"PK\x06\x06")
_HEADER = struct.Struct("<4sHHHHHIIIHH")
_STORED, _DEFLATED = 0, 8
_ENCRYPTED, _DATA_DESCRIPTOR = 0x1, 0x8
_ZIP64 = 0xFFFFFFFF
_PIECE = 1 << 20

Keep = Callable[[str], bool]
#: Bytes read so far, and the member passing.
Progress = Callable[[int, str], None]


@dataclass
class StreamResult:
    kept: int = 0
    kept_bytes: int = 0
    skipped: int = 0
    read_bytes: int = 0


class _Reader:
    """Exact reads over an iterator of chunks, counting what has been consumed."""

    def __init__(self, chunks: Iterable[bytes]) -> None:
        self._chunks: Iterator[bytes] = iter(chunks)
        self._buffer = bytearray()
        self.consumed = 0

    def _fill(self, size: int) -> None:
        while len(self._buffer) < size:
            chunk = next(self._chunks, None)
            if chunk is None:
                raise ValueError("The download ended in the middle of the archive.")
            self._buffer += chunk

    def peek(self, size: int) -> bytes:
        self._fill(size)
        return bytes(self._buffer[:size])

    def read(self, size: int) -> bytes:
        self._fill(size)
        data = bytes(self._buffer[:size])
        del self._buffer[:size]
        self.consumed += size
        return data

    def pieces(self, size: int) -> Iterator[bytes]:
        """`size` bytes in pieces, without holding a large member in memory."""
        left = size
        while left:
            piece = self.read(min(left, _PIECE))
            left -= len(piece)
            yield piece


def safe_member(name: str) -> PurePosixPath:
    """The member's relative path, or ValueError for one that would leave the folder."""
    path = PurePosixPath(name.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or (path.parts and ":" in path.parts[0]):
        raise ValueError(f"The archive names a file outside its folder: {name!r}.")
    return path


def stream_unzip(
    chunks: Iterable[bytes], dest: Path, keep: Keep, progress: Progress
) -> StreamResult:
    """Unpack the members `keep` accepts into `dest`; the rest are read past."""
    reader, result = _Reader(chunks), StreamResult()
    while True:
        signature = reader.peek(4)
        if signature in _END_MARKERS:
            break
        if signature != _LOCAL:
            raise ValueError("This is not a ZIP archive, or it is damaged.")
        _sig, _ver, flags, method, _t, _d, crc, size, raw_size, name_len, extra_len = (
            _HEADER.unpack(reader.read(_HEADER.size))
        )
        name = reader.read(name_len).decode("utf-8", errors="replace")
        reader.read(extra_len)
        _check(name, flags, method, size, raw_size)
        progress(reader.consumed, name)
        if name.endswith("/") or not keep(name):
            for _piece in reader.pieces(size):
                pass
            result.skipped += 0 if name.endswith("/") else 1
        else:
            result.kept_bytes += _write(reader, dest / safe_member(name), method, size, crc)
            result.kept += 1
        result.read_bytes = reader.consumed
    return result


def _check(name: str, flags: int, method: int, size: int, raw_size: int) -> None:
    if flags & _DATA_DESCRIPTOR:
        raise ValueError(f"{name}: the archive puts sizes after the data; it cannot be streamed.")
    if flags & _ENCRYPTED:
        raise ValueError(f"{name}: the archive is encrypted.")
    if _ZIP64 in (size, raw_size):
        raise ValueError(f"{name}: members over 4 GB (ZIP64) are not supported.")
    if method not in (_STORED, _DEFLATED):
        raise ValueError(f"{name}: compression method {method} is not supported.")


def _write(reader: _Reader, target: Path, method: int, size: int, crc: int) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    inflate = zlib.decompressobj(-zlib.MAX_WBITS) if method == _DEFLATED else None
    written, check = 0, 0
    with target.open("wb") as handle:
        for piece in reader.pieces(size):
            data = inflate.decompress(piece) if inflate else piece
            handle.write(data)
            written, check = written + len(data), zlib.crc32(data, check)
        if inflate:
            tail = inflate.flush()
            handle.write(tail)
            written, check = written + len(tail), zlib.crc32(tail, check)
    if check != crc:
        raise ValueError(f"{target.name}: the download is damaged (checksum mismatch).")
    return written

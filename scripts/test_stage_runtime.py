"""Tests for scripts/stage_runtime.py (doc 126).

    backend/.venv/bin/python -m pytest scripts/test_stage_runtime.py

No network: the uv download is replaced; what is checked is what ships and that a bad
checksum stops the build.
"""

from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stage_runtime


def _fake_backend(root: Path) -> Path:
    backend = root / "backend"
    (backend / "app" / "ml").mkdir(parents=True)
    (backend / "app" / "main.py").write_text("print('app')")
    (backend / "app" / "ml" / "head.py").write_text("")
    (backend / "app" / "__pycache__").mkdir()
    (backend / "app" / "__pycache__" / "main.cpython-312.pyc").write_bytes(b"\0")
    (backend / "tests").mkdir()
    (backend / "tests" / "test_x.py").write_text("")
    (backend / ".venv").mkdir()
    (backend / ".env").write_text("HF_TOKEN=secret")
    (backend / "pyproject.toml").write_text("[project]\nname='x'\n")
    # Bytes: write_text would give "\r\n" on Windows, and another hash.
    (backend / "uv.lock").write_bytes(b"version = 1\n")
    return backend


def test_only_the_package_and_uvs_two_files_ship(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(stage_runtime, "BACKEND", _fake_backend(tmp_path))
    out = tmp_path / "out"
    count = stage_runtime.copy_backend(out)
    shipped = sorted(
        p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()
    )
    assert shipped == ["app/main.py", "app/ml/head.py", "pyproject.toml", "uv.lock"]
    assert count == 4


def test_stage_writes_uv_and_the_lock_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    backend = _fake_backend(tmp_path)
    monkeypatch.setattr(stage_runtime, "BACKEND", backend)
    monkeypatch.setattr(stage_runtime, "fetch_uv", lambda target: b"uv-binary")
    out = tmp_path / "runtime"
    # A previous staging must not leak into this one.
    (out / "stale").mkdir(parents=True)

    version = stage_runtime.stage("aarch64-apple-darwin", out)

    assert (out / "uv").read_bytes() == b"uv-binary"
    if sys.platform != "win32":  # Windows has no execute bit; uv.exe runs by its name
        assert (out / "uv").stat().st_mode & 0o111, "uv must be executable"
    assert not (out / "stale").exists()
    assert version["lock_sha256"] == hashlib.sha256(b"version = 1\n").hexdigest()
    assert json.loads((out / "VERSION.json").read_text()) == version


def test_windows_gets_uv_exe(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(stage_runtime, "BACKEND", _fake_backend(tmp_path))
    monkeypatch.setattr(stage_runtime, "fetch_uv", lambda target: b"exe")
    out = tmp_path / "runtime"
    stage_runtime.stage("x86_64-pc-windows-msvc", out)
    assert (out / "uv.exe").is_file() and not (out / "uv").exists()


def test_unknown_target_is_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="Unknown target"):
        stage_runtime.stage("x86_64-apple-darwin", tmp_path / "runtime")


def _tar_with_uv(content: bytes) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tarred:
        info = tarfile.TarInfo("uv-aarch64-apple-darwin/uv")
        info.size = len(content)
        tarred.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


def test_uv_is_verified_against_the_published_checksum(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    archive = _tar_with_uv(b"real uv")
    good = hashlib.sha256(archive).hexdigest()
    responses = {"": archive, ".sha256": f"{good}  uv.tar.gz\n".encode()}
    monkeypatch.setattr(
        stage_runtime,
        "_fetch",
        lambda url: responses[".sha256" if url.endswith(".sha256") else ""],
    )
    assert stage_runtime.fetch_uv("aarch64-apple-darwin") == b"real uv"

    responses[".sha256"] = b"0" * 64
    with pytest.raises(SystemExit, match="checksum"):
        stage_runtime.fetch_uv("aarch64-apple-darwin")

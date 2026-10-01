"""Tests for scripts/bump_version.py."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import bump_version

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def copy(tmp_path: Path) -> Path:
    names = [name for name, _ in bump_version.TEXT_FILES] + [
        n for n, _ in bump_version.JSON_FILES
    ]
    for name in names:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / name, tmp_path / name)
    return tmp_path


def test_every_place_gets_the_version(copy: Path) -> None:
    bump_version.bump("9.8.7", copy)
    conf = json.loads((copy / "apps/desktop/src-tauri/tauri.conf.json").read_text())
    assert conf["version"] == "9.8.7"
    lock = json.loads((copy / "apps/frontend/package-lock.json").read_text())
    assert lock["version"] == lock["packages"][""]["version"] == "9.8.7"
    assert '__version__ = "9.8.7"' in (copy / "backend/app/__init__.py").read_text()
    assert (
        'version = "9.8.7"' in (copy / "apps/desktop/src-tauri/Cargo.toml").read_text()
    )


def test_dependencies_keep_their_versions(copy: Path) -> None:
    before = json.loads((copy / "apps/frontend/package-lock.json").read_text())
    bump_version.bump("9.8.7", copy)
    after = json.loads((copy / "apps/frontend/package-lock.json").read_text())
    deps = {k: v.get("version") for k, v in after["packages"].items() if k}
    assert deps == {k: v.get("version") for k, v in before["packages"].items() if k}


def test_a_bad_version_is_refused(copy: Path) -> None:
    with pytest.raises(SystemExit):
        bump_version.bump("1.0", copy)

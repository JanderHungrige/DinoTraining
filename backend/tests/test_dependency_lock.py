"""The lock users install from (doc 125): current, one PyTorch per machine, hashed."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
LOCK = tomllib.loads((BACKEND / "uv.lock").read_text(encoding="utf-8"))
PROJECT = tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))


def _uv() -> str | None:
    beside = Path(sys.executable).with_name("uv")
    return str(beside) if beside.is_file() else shutil.which("uv")


def test_the_lock_is_current_with_pyproject() -> None:
    uv = _uv()
    if uv is None:
        pytest.skip("uv is not installed here; CI's lock-check runs this")
    result = subprocess.run(
        [uv, "lock", "--check", "--offline"], cwd=BACKEND, capture_output=True, text=True
    )
    assert result.returncode == 0, result.stderr


def _wheels(name: str, version: str) -> list[dict[str, str]]:
    [package] = [p for p in LOCK["package"] if p["name"] == name and p["version"] == version]
    wheels: list[dict[str, str]] = package["wheels"]
    return wheels


def _platforms(wheels: list[dict[str, str]]) -> set[str]:
    found = set()
    for wheel in wheels:
        url = wheel["url"]
        found.add(
            "mac"
            if "macosx" in url and "arm64" in url
            else "win"
            if "win_amd64" in url
            else "linux"
            if "linux_x86_64" in url or "manylinux_2_28_x86_64" in url
            else "other"
        )
    return found - {"other"}


@pytest.mark.parametrize(
    ("version", "platforms"),
    [
        ("2.13.0", {"mac"}),  # PyPI: the Mac's (MPS)
        ("2.13.0+cpu", {"win", "linux"}),
        ("2.13.0+cu126", {"win", "linux"}),
        ("2.13.0+cu130", {"win", "linux"}),
    ],
)
def test_every_machine_has_its_torch_with_hashes(version: str, platforms: set[str]) -> None:
    wheels = _wheels("torch", version)
    assert platforms <= _platforms(wheels)
    assert all("hash" in wheel for wheel in wheels)


def test_torch_is_never_an_unconditional_dependency() -> None:
    """One variant per machine: in the base dependencies it would be installed twice."""
    assert not [
        d for d in PROJECT["project"]["dependencies"] if d.startswith(("torch", "torchvision"))
    ]
    assert PROJECT["tool"]["uv"]["conflicts"] == [
        [{"extra": "cpu"}, {"extra": "cu126"}, {"extra": "cu130"}]
    ]


def test_runtime_imports_are_declared_not_inherited() -> None:
    """httpx (doc 123's MLflow client) came in only through mcp before doc 125."""
    assert any(d.startswith("httpx") for d in PROJECT["project"]["dependencies"])

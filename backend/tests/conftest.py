"""Pytest configuration.

Puts ``backend/`` on the import path so ``app`` resolves regardless of how pytest
is invoked, and keeps the developer's real ``.env`` out of the test run.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

import pytest  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_settings(
    monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory
) -> Iterator[None]:
    """Tests must not inherit the developer's local .env or exported secrets.

    Deleting the environment variables is not sufficient on its own: ``get_settings()``
    also reads a ``.env`` file, and pydantic-settings reads it whatever the environment
    says. ``DINO_ENV_FILE`` is therefore pointed at a path that does not exist, so the file
    layer contributes nothing. Before this, the suite was accidentally safe only because
    the resolved path was wrong and no file was found there.
    """
    monkeypatch.setenv(
        "DINO_ENV_FILE", str(tmp_path_factory.mktemp("env") / "absent.env")
    )
    for key in (
        "HF_TOKEN",
        "DINO_MODEL_CACHE_DIR",
        "DINO_API_HOST",
        "DINO_API_PORT",
        "DINO_API_PREFIX",
        "DINO_DEVICE",
        "DINO_DATA_DIR",
        "LOG_LEVEL",
    ):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def head_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    """Settings pointed at a throwaway data + model root.

    Head installs write both a SQLite row and a weights file, so a shared fixture keeps
    every install test from leaking into the developer's real application-support
    directory — which Wave 2 already had to clean up by hand once.
    """
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_MODEL_CACHE_DIR", str(tmp_path / "models"))
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(autouse=True)
def _no_real_downloads(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail loudly if a test reaches the real snapshot_download.

    A test that falls through to the real thing quietly pulls hundreds of MB and
    makes the suite depend on the network. Tests that exercise the download path
    override this with their own patch.
    """
    import huggingface_hub

    def _blocked(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "Test attempted a real huggingface_hub.snapshot_download. "
            "Patch it in the test instead."
        )

    monkeypatch.setattr(huggingface_hub, "snapshot_download", _blocked)

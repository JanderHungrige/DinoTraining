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

from app.core.config import get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_settings(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Tests must not inherit the developer's local .env or exported secrets."""
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

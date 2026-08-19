"""Shared setup for the dataset API tests.

Boxes and masks are tested in separate modules — one responsibility per file — but they
need the same throwaway data root and the same dataset-creation helper. Following the
`inference_api_testkit` pattern: this module exports plain functions, and each test module
wraps the generator in its own fixture, so no fixture is imported across modules.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.datasets.db import reset_connection
from app.main import create_app


async def dataset_client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    """An AsyncClient over the real ASGI app, pointed at a throwaway data root."""
    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    reset_connection()

    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    reset_connection()


async def make_dataset(client: AsyncClient, **kwargs: Any) -> dict[str, Any]:
    payload = {"name": "Cats", **kwargs}
    response = await client.post("/api/v1/datasets", json=payload)
    assert response.status_code == 201
    body: dict[str, Any] = response.json()
    return body


def mask_payload(*labels: str, width: int = 4, height: int = 4) -> dict[str, Any]:
    """One 4x4 image with a 2x2 block mask per label.

    Counts are column-major with a leading background run: the block occupies rows 1-2 of
    columns 1 and 2, i.e. flat indices 5,6 and 9,10 of a 16-pixel frame.
    """
    counts = [5, 2, 2, 2, 5]
    return {
        "path": "/images/a.jpg",
        "width": width,
        "height": height,
        "masks": [
            {
                "label": label,
                "provenance": "sam3",
                "rle": {"size": [height, width], "counts": counts},
            }
            for label in labels
        ],
    }

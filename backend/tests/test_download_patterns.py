"""The download must fetch safetensors only, never the duplicate pickle.

A HuggingFace repo usually publishes the same tensors twice. This project loads safetensors
only, so fetching the pickle doubled every download and left a file on disk the app refuses
to open. Measured before the fix: grounding-dino-tiny used 1.3 GB against a 690 MB estimate,
dinov2-small 168 MB against 88 MB, sam2.1-hiera-small 352 MB against 184 MB.

These tests assert the exclusion is actually passed to snapshot_download, because the symptom
is invisible to every other test — a repo downloaded with or without its pickle looks
identical to `is_installed`, and the catalogue's size field is just a number in a dataclass.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.ml.downloads import PICKLE_PATTERNS, _download
from app.ml.registry import ModelSpec, all_models


class _Job:
    """Minimal stand-in for DownloadJob — _download only needs the tqdm hook."""

    def report_bar(self, bar_id: int, current: int, total: int) -> None: ...


def _spec() -> ModelSpec:
    spec = next(s for s in all_models() if s.id == "sam2.1-hiera-small")
    return spec


def _capture(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    captured: dict[str, Any] = {}

    def fake_snapshot_download(**kwargs: Any) -> str:
        captured.update(kwargs)
        return str(kwargs["local_dir"])

    import huggingface_hub

    monkeypatch.setattr(huggingface_hub, "snapshot_download", fake_snapshot_download)
    return captured


class TestIgnorePatterns:
    def test_the_pickle_formats_are_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        captured = _capture(monkeypatch)
        _download(_Job(), _spec(), tmp_path, None)  # type: ignore[arg-type]

        ignored = set(captured["ignore_patterns"])
        assert {"*.bin", "*.pt", "*.pth"} <= ignored

    def test_safetensors_are_not_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The obvious way to break this fix is to over-match and download nothing usable."""
        captured = _capture(monkeypatch)
        _download(_Job(), _spec(), tmp_path, None)  # type: ignore[arg-type]

        for pattern in captured["ignore_patterns"]:
            assert "safetensors" not in pattern
        assert "*.json" not in captured["ignore_patterns"]

    def test_every_excluded_pattern_is_a_weight_format(self) -> None:
        """Excluding a config or tokenizer file would break loading in a way tests miss."""
        for pattern in PICKLE_PATTERNS:
            assert pattern.startswith("*.")
            assert pattern not in ("*.json", "*.txt", "*.yaml", "*.model")

    def test_the_exclusion_applies_to_gated_downloads_too(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A token in the kwargs must not displace the ignore list."""
        captured = _capture(monkeypatch)
        _download(_Job(), _spec(), tmp_path, "hf_token")  # type: ignore[arg-type]

        assert captured["token"] == "hf_token"
        assert "*.bin" in captured["ignore_patterns"]

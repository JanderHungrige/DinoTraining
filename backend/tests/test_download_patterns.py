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


class TestFailureMessages:
    """A 403 must say the right thing, and there are three different right things."""

    def test_an_approval_gated_model_says_the_request_is_pending(self) -> None:
        from app.ml.downloads import failure_message

        message = failure_message(_spec_for("sam3"), _forbidden())
        assert "has not been granted yet" in message
        assert "by a person" in message
        # The opposite advice would be actively misleading: the token is fine.
        assert "check your token" not in message.lower()

    def test_a_terms_only_gated_model_points_at_the_licence(self) -> None:
        from app.ml.downloads import failure_message

        message = failure_message(_spec_for("dinov3-vitb16"), _forbidden())
        assert "Accept the" in message
        assert "has not been granted yet" not in message

    def test_an_open_model_gets_the_generic_message(self) -> None:
        from app.ml.downloads import failure_message

        message = failure_message(_spec_for("dinov2-small"), _forbidden())
        assert "facebook/dinov2-small" in message

    def test_no_failure_message_leaks_the_exception_text(self) -> None:
        """HuggingFace errors embed the request URL, and a token can ride along in it."""
        from app.ml.downloads import failure_message

        secret = "hf_supersecrettoken"
        error = RuntimeError(f"401 for https://huggingface.co/api?token={secret}")
        for model_id in ("sam3", "dinov3-vitb16", "dinov2-small"):
            assert secret not in failure_message(_spec_for(model_id), error)


def _spec_for(model_id: str) -> ModelSpec:
    spec = next(s for s in all_models() if s.id == model_id)
    return spec


def _forbidden() -> Exception:
    class _Response:
        status_code = 403

    class _HttpError(Exception):
        response = _Response()

    return _HttpError("forbidden")

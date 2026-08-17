"""Tests for app.core.config — settings loading, device resolution, token masking."""

from __future__ import annotations

import pytest

from app.core.config import Settings, resolve_device


class TestResolveDevice:
    def test_explicit_cpu_is_returned_as_is(self) -> None:
        assert resolve_device("cpu") == "cpu"

    def test_auto_resolves_to_an_available_device(self) -> None:
        device = resolve_device("auto")
        assert device in {"cuda", "mps", "cpu"}

    def test_unavailable_explicit_device_raises(self) -> None:
        """An explicit device that isn't present must fail loudly, not downgrade silently."""
        import torch

        if torch.cuda.is_available():
            pytest.skip("CUDA is available on this machine; cannot test the failure path")
        with pytest.raises(RuntimeError, match="cuda"):
            resolve_device("cuda")

    def test_unknown_device_raises(self) -> None:
        with pytest.raises(ValueError, match="tpu"):
            resolve_device("tpu")


class TestSettings:
    def test_defaults_match_env_example(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.api_host == "127.0.0.1"
        assert settings.api_port == 8756
        assert settings.api_prefix == "/api/v1"
        assert settings.log_level == "INFO"

    def test_host_is_loopback_by_default(self) -> None:
        """The sidecar must not be reachable off-machine — see doc Security section."""
        settings = Settings(_env_file=None)
        assert settings.api_host not in {"0.0.0.0", "::"}

    def test_hf_token_is_masked_in_repr(self) -> None:
        settings = Settings(_env_file=None, hf_token="hf_supersecretvalue")
        assert "hf_supersecretvalue" not in repr(settings)
        assert "hf_supersecretvalue" not in str(settings)

    def test_hf_token_value_is_still_readable(self) -> None:
        settings = Settings(_env_file=None, hf_token="hf_supersecretvalue")
        assert settings.hf_token is not None
        assert settings.hf_token.get_secret_value() == "hf_supersecretvalue"

    def test_hf_token_defaults_to_none_when_absent(self) -> None:
        settings = Settings(_env_file=None)
        assert settings.hf_token is None

    def test_resolved_device_is_concrete(self) -> None:
        settings = Settings(_env_file=None, device="auto")
        assert settings.resolved_device in {"cuda", "mps", "cpu"}

"""Tests for the token and licence endpoints.

The security properties are the point: a token goes in, and nothing anywhere gives it back.
Several of these assert on the *raw response text* rather than a parsed field, because a
leak would most likely appear somewhere nobody thought to parse.
"""

from __future__ import annotations

import stat
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.env_file import mask_secret, read_env, write_env_value
from app.main import create_app

TOKEN = "hf_averysecrettokenvalue123"


@pytest.fixture
def env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / ".env"
    monkeypatch.setenv("DINO_ENV_FILE", str(path))
    get_settings.cache_clear()
    return path


@pytest.fixture
def client(env_file: Path) -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c
    get_settings.cache_clear()


class TestTokenStatus:
    def test_it_reports_no_token_on_a_clean_install(self, client: TestClient) -> None:
        body = client.get("/api/v1/settings/hf-token").json()
        assert body["configured"] is False
        assert body["hint"] is None

    def test_it_reports_where_the_file_is(self, client: TestClient, env_file: Path) -> None:
        """The user must be able to find the file to edit it by hand."""
        body = client.get("/api/v1/settings/hf-token").json()
        assert body["env_file"] == str(env_file)


class TestSaveToken:
    def test_it_saves_and_reports_configured(self, client: TestClient) -> None:
        body = client.put("/api/v1/settings/hf-token", json={"token": TOKEN}).json()
        assert body["configured"] is True

    def test_it_writes_the_token_to_the_env_file(
        self, client: TestClient, env_file: Path
    ) -> None:
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        assert read_env(env_file)["HF_TOKEN"] == TOKEN

    def test_the_response_never_contains_the_token(self, client: TestClient) -> None:
        """Asserted on raw text: a leak would surface in a field nobody parses."""
        response = client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        assert TOKEN not in response.text

    def test_the_status_endpoint_never_contains_the_token(
        self, client: TestClient
    ) -> None:
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        assert TOKEN not in client.get("/api/v1/settings/hf-token").text

    def test_the_hint_identifies_without_disclosing(self, client: TestClient) -> None:
        body = client.put("/api/v1/settings/hf-token", json={"token": TOKEN}).json()
        assert body["hint"].endswith(TOKEN[-4:])
        assert TOKEN[:-4] not in body["hint"]

    def test_the_file_is_not_world_readable(
        self, client: TestClient, env_file: Path
    ) -> None:
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        mode = stat.S_IMODE(env_file.stat().st_mode)
        assert mode & stat.S_IRGRP == 0
        assert mode & stat.S_IROTH == 0

    def test_a_saved_token_is_visible_immediately_without_a_restart(
        self, client: TestClient
    ) -> None:
        """uvicorn does not reload and settings are cached, so the cache must be cleared.

        Without that, the user saves a token and the very next download still reports
        none — which looks exactly like the save silently failing.
        """
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        secret = get_settings().hf_token
        assert secret is not None
        assert secret.get_secret_value() == TOKEN

    def test_a_saved_token_unlocks_gated_models_immediately(
        self, client: TestClient
    ) -> None:
        """The end-to-end effect the user is actually after."""
        before = client.get("/api/v1/models").json()["models"]
        assert any(m["gated"] and not m["available"] for m in before)

        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})

        after = client.get("/api/v1/models").json()["models"]
        assert all(m["available"] for m in after)

    def test_an_obviously_wrong_value_is_422(self, client: TestClient) -> None:
        response = client.put("/api/v1/settings/hf-token", json={"token": "abc"})
        assert response.status_code == 422
        assert "huggingface.co/settings/tokens" in response.json()["error"]["message"]

    def test_an_empty_token_is_rejected(self, client: TestClient) -> None:
        assert client.put("/api/v1/settings/hf-token", json={"token": ""}).status_code == 422


class TestClearToken:
    def test_it_removes_the_token(self, client: TestClient) -> None:
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        body = client.delete("/api/v1/settings/hf-token").json()
        assert body["configured"] is False
        assert get_settings().hf_token is None


class TestPreservesTheFile:
    def test_other_keys_survive_a_token_write(
        self, client: TestClient, env_file: Path
    ) -> None:
        write_env_value("DINO_DEVICE", "cpu", env_file)
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        assert read_env(env_file)["DINO_DEVICE"] == "cpu"

    def test_comments_survive_a_token_write(
        self, client: TestClient, env_file: Path
    ) -> None:
        """The file is the user's. Rewriting it from a dict would delete their notes."""
        env_file.write_text("# my notes\nHF_TOKEN=\n# keep me\n", encoding="utf-8")
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        text = env_file.read_text(encoding="utf-8")
        assert "# my notes" in text
        assert "# keep me" in text

    def test_the_token_key_is_replaced_not_duplicated(
        self, client: TestClient, env_file: Path
    ) -> None:
        client.put("/api/v1/settings/hf-token", json={"token": TOKEN})
        client.put("/api/v1/settings/hf-token", json={"token": "hf_secondvalue9999"})
        lines = env_file.read_text(encoding="utf-8").splitlines()
        assert sum(1 for line in lines if line.startswith("HF_TOKEN=")) == 1


class TestLicences:
    def test_only_gated_models_need_a_notice(self, client: TestClient) -> None:
        notices = client.get("/api/v1/settings/licences").json()["notices"]
        ids = {n["model_id"] for n in notices}
        assert "sam3" in ids
        assert "dinov2-small" not in ids, "an open model needs no acknowledgement"

    def test_the_approval_model_explains_the_extra_step(self, client: TestClient) -> None:
        notices = client.get("/api/v1/settings/licences").json()["notices"]
        sam3 = next(n for n in notices if n["model_id"] == "sam3")
        assert sam3["requires_access_request"] is True
        assert "never downloads it for you" in sam3["explanation"]
        assert "request access" in sam3["explanation"].lower()

    def test_a_terms_only_model_does_not_promise_manual_approval(
        self, client: TestClient
    ) -> None:
        notices = client.get("/api/v1/settings/licences").json()["notices"]
        dinov3 = next(n for n in notices if n["model_id"] == "dinov3-vitb16")
        assert dinov3["requires_access_request"] is False
        assert "immediate" in dinov3["explanation"]

    def test_accepting_a_licence_is_recorded(self, client: TestClient) -> None:
        body = client.post(
            "/api/v1/settings/accepted-licences", json={"model_id": "sam3"}
        ).json()
        assert "sam3" in body["accepted_licences"]

        notices = client.get("/api/v1/settings/licences").json()["notices"]
        assert next(n for n in notices if n["model_id"] == "sam3")["accepted"] is True

    def test_accepting_twice_does_not_duplicate(self, client: TestClient) -> None:
        client.post("/api/v1/settings/accepted-licences", json={"model_id": "sam3"})
        body = client.post(
            "/api/v1/settings/accepted-licences", json={"model_id": "sam3"}
        ).json()
        assert body["accepted_licences"].count("sam3") == 1

    def test_an_unknown_model_is_404(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/settings/accepted-licences", json={"model_id": "not-a-model"}
        )
        assert response.status_code == 404


class TestMasking:
    def test_a_short_secret_is_masked_entirely(self) -> None:
        """Four characters of an eight-character secret is half of it."""
        assert mask_secret("abcd1234") == "•" * 8

    def test_none_stays_none(self) -> None:
        assert mask_secret(None) is None

    def test_an_empty_string_stays_none(self) -> None:
        assert mask_secret("") is None

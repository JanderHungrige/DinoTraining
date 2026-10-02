"""Doc 147: cloud storage connections, their secrets in .env only, and one storage interface."""

from __future__ import annotations

import base64
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.cloud.connections import ConnectionRequest, create_connection, service_account_json
from app.cloud.errors import CloudError
from app.cloud.storage import memory_storage, probe_storage

SECRET = "SUPERSECRET-0123456789"
GCS_KEY = {
    "type": "service_account",
    "project_id": "p",
    "private_key": "-----BEGIN-----x",
    "client_email": "a@p.iam",
}


@pytest.fixture(autouse=True)
def _isolated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import get_settings
    from app.datasets.db import reset_connection

    monkeypatch.setenv("DINO_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("DINO_ENV_FILE", str(tmp_path / ".env"))
    get_settings.cache_clear()
    reset_connection()


@pytest.fixture
def client() -> TestClient:
    from app.main import create_app

    return TestClient(create_app())


S3 = {"name": "MinIO", "kind": "s3", "endpoint": "http://127.0.0.1:9", "region": "us-east-1"}


def test_secrets_go_in_and_never_come_out(
    client: TestClient, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    made = client.post(
        "/api/v1/cloud/connections",
        json={**S3, "secrets": {"access_key": "AK", "secret_key": SECRET}},
    )
    assert made.status_code == 201
    connection = made.json()
    assert connection["secrets_set"] == ["access_key", "secret_key"]
    listed = client.get("/api/v1/cloud/connections")
    env = (tmp_path / ".env").read_text()
    assert f"DINO_CLOUD_{connection['id'].upper()}_SECRET_KEY={SECRET}" in env
    tested = client.post(
        f"/api/v1/cloud/connections/{connection['id']}/test", json={"bucket": "photos"}
    )
    for text in (made.text, listed.text, tested.text, caplog.text):
        assert SECRET not in text

    kept = client.put(
        f"/api/v1/cloud/connections/{connection['id']}",
        json={**S3, "name": "Lab MinIO", "secrets": {"secret_key": ""}},
    )
    assert kept.json()["name"] == "Lab MinIO" and kept.json()["secrets_set"] == [
        "access_key",
        "secret_key",
    ]
    assert SECRET in (tmp_path / ".env").read_text()  # an empty secret keeps the stored one

    assert client.delete(f"/api/v1/cloud/connections/{connection['id']}").json() == {
        "deleted": True
    }
    assert client.get("/api/v1/cloud/connections").json() == []
    assert SECRET not in (tmp_path / ".env").read_text()


def test_an_unreachable_endpoint_is_said_plainly_and_quickly(client: TestClient) -> None:
    made = client.post(
        "/api/v1/cloud/connections",
        json={**S3, "secrets": {"access_key": "AK", "secret_key": SECRET}},
    ).json()
    tested = client.post(
        f"/api/v1/cloud/connections/{made['id']}/test", json={"bucket": "photos"}
    ).json()
    assert tested["ok"] is False
    assert "could not be reached" in tested["message"]
    assert (
        client.post("/api/v1/cloud/connections/nope/test", json={"bucket": "b"}).status_code == 404
    )


@pytest.mark.parametrize(
    ("body", "reason"),
    [
        ({"name": "Az", "kind": "azure", "secrets": {"account_key": "k"}}, "account's name"),
        ({**S3, "secrets": {"account_key": "k"}}, "has no account_key"),
        ({**S3, "endpoint": "minio:9000"}, "http:// or https://"),
        (
            {"name": "G", "kind": "gcs", "secrets": {"service_account": '{"type": "user"}'}},
            "not a service account",
        ),
        (
            {"name": "G", "kind": "gcs", "secrets": {"service_account": "not json, not base64!"}},
            "neither JSON",
        ),
    ],
)
def test_what_cannot_work_is_refused(
    client: TestClient, body: dict[str, object], reason: str
) -> None:
    refused = client.post("/api/v1/cloud/connections", json=body)
    assert refused.status_code == 422 and reason in refused.json()["error"]["message"]


def test_a_pasted_gcs_key_is_kept_on_one_line_and_read_back(tmp_path: Path) -> None:
    made = create_connection(
        ConnectionRequest(
            name="G", kind="gcs", secrets={"service_account": json.dumps(GCS_KEY, indent=2)}
        )
    )
    line = next(
        line for line in (tmp_path / ".env").read_text().splitlines() if "SERVICE_ACCOUNT" in line
    )
    assert "\n" not in line and "{" not in line  # base64 on one line (decision D4)
    assert json.loads(base64.b64decode(line.split("=", 1)[1])) == GCS_KEY
    assert json.loads(service_account_json(made.id) or "") == GCS_KEY


def test_the_storage_verbs_and_a_refused_overwrite() -> None:
    storage = memory_storage("bucket")
    assert probe_storage(storage) == "Connected to bucket; it is empty."
    first = storage.put_if("a/labels.json", b"v1", None)  # only if absent
    assert storage.get("a/labels.json") == b"v1"
    entry = storage.head("a/labels.json")
    assert entry is not None and entry.size == 2 and entry.e_tag == first
    second = storage.put_if("a/labels.json", b"v2", first)
    with pytest.raises(CloudError, match="changed since it was last read"):
        storage.put_if("a/labels.json", b"stale", first)  # someone else wrote v2 meanwhile
    with pytest.raises(CloudError):
        storage.put_if("a/labels.json", b"again", None)  # "only if absent" no longer holds
    assert storage.get("a/labels.json") == b"v2" and second != first
    assert storage.head("missing") is None
    for index in range(3):
        storage.put(f"pics/{index}.jpg", b"x")
    assert sorted(entry.key for page in storage.list("pics") for entry in page) == [
        "pics/0.jpg",
        "pics/1.jpg",
        "pics/2.jpg",
    ]
    assert "holds files" in probe_storage(storage)


def test_a_missing_bucket_is_named_and_a_german_reader_reads_german(client: TestClient) -> None:
    from app.cloud.errors import explain

    s3 = explain(RuntimeError("Generic S3 error: ... <Code>NoSuchBucket</Code> ..."), "gone")
    azure = explain(
        RuntimeError("ContainerNotFound: The specified container does not exist."), "box"
    )
    assert "gone does not exist" in str(s3) and "box does not exist" in str(azure)

    made = client.post(
        "/api/v1/cloud/connections",
        json={**S3, "secrets": {"access_key": "AK", "secret_key": SECRET}},
    ).json()
    german = client.post(
        f"/api/v1/cloud/connections/{made['id']}/test",
        json={"bucket": "photos"},
        headers={"Accept-Language": "de"},
    ).json()
    assert german["message"].startswith(
        "Der Speicher war nicht erreichbar. Prüf Endpunkt und Netzwerk."
    )
    refused = client.post(
        "/api/v1/cloud/connections",
        json={"name": "Az", "kind": "azure"},
        headers={"Accept-Language": "de"},
    )
    assert refused.json()["error"]["message"] == "Azure braucht den Namen des Speicherkontos."

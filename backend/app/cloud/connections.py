"""A cloud storage account (doc 147): the non-secret parts in the database, the secrets in
`.env` under `DINO_CLOUD_<ID>_<PART>`, never returned, logged or stored anywhere else."""

from __future__ import annotations

import base64
import binascii
import json
import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.core.env_file import read_env, write_env_value
from app.datasets.db import transaction

Kind = Literal["s3", "azure", "gcs"]

#: The secret parts each kind can hold. Azure takes an account key or a SAS token.
SECRETS: dict[Kind, tuple[str, ...]] = {
    "s3": ("access_key", "secret_key"),
    "azure": ("account_key", "sas_token"),
    "gcs": ("service_account",),
}

TABLE = """
CREATE TABLE IF NOT EXISTS cloud_connections (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    kind       TEXT NOT NULL CHECK (kind IN ('s3', 'azure', 'gcs')),
    endpoint   TEXT,
    region     TEXT,
    account    TEXT,
    created_at TEXT NOT NULL
)
"""


class ConnectionFields(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    kind: Kind
    #: Empty for AWS / Azure / GCS themselves; a URL for MinIO, R2, Azurite and the like.
    endpoint: str | None = None
    region: str | None = None
    #: Azure: the storage account's name.
    account: str | None = None


class ConnectionRequest(ConnectionFields):
    #: Absent or empty: keep what is stored. Never returned.
    secrets: dict[str, str] = {}


class Connection(ConnectionFields):
    id: str
    created_at: str
    #: Which secret parts are set; never their values.
    secrets_set: list[str]


def _key(connection_id: str, part: str) -> str:
    return f"DINO_CLOUD_{connection_id.upper()}_{part.upper()}"


def _ensure_table(settings: Settings | None) -> None:
    with transaction(settings) as connection:
        connection.execute(TABLE)


def _secrets_set(connection_id: str, kind: Kind) -> list[str]:
    env = read_env()
    return [part for part in SECRETS[kind] if env.get(_key(connection_id, part))]


def secret(connection_id: str, part: str) -> str | None:
    """A secret part for building a store; the only reader of the values."""
    return read_env().get(_key(connection_id, part)) or None


def _check(fields: ConnectionFields, secrets: dict[str, str]) -> None:
    unknown = set(secrets) - set(SECRETS[fields.kind])
    if unknown:
        raise ValueError(f"A {fields.kind} connection has no {', '.join(sorted(unknown))}.")
    if fields.kind == "azure" and not (fields.account or "").strip():
        raise ValueError("Azure needs the storage account's name.")
    if fields.endpoint and not fields.endpoint.startswith(("http://", "https://")):
        raise ValueError("The endpoint must start with http:// or https://.")
    key = secrets.get("service_account", "").strip()
    if key:
        _service_account_json(key)  # a ValueError that says what is wrong


def _service_account_json(value: str) -> str:
    """The GCS key as JSON: pasted JSON, or base64 of it as `.env` keeps it (decision D4)."""
    text = value.strip()
    if not text.startswith("{"):
        try:
            text = base64.b64decode(text, validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError) as error:
            raise ValueError("The service account key is neither JSON nor base64 of it.") from error
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError("The service account key is not valid JSON.") from error
    if not isinstance(parsed, dict) or parsed.get("type") != "service_account":
        raise ValueError(
            'This JSON is not a service account key (its "type" is not service_account).'
        )
    return text


def service_account_json(connection_id: str) -> str | None:
    stored = secret(connection_id, "service_account")
    return _service_account_json(stored) if stored else None


def _write_secrets(connection_id: str, secrets: dict[str, str]) -> None:
    for part, value in secrets.items():
        value = value.strip()
        if not value:
            continue  # empty: keep the stored one
        if part == "service_account":  # one line in .env, whatever was pasted
            value = base64.b64encode(_service_account_json(value).encode()).decode()
        write_env_value(_key(connection_id, part), value)


def _view(row: dict[str, str]) -> Connection:
    kind: Kind = row["kind"]  # type: ignore[assignment]
    return Connection(**row, secrets_set=_secrets_set(row["id"], kind))


def list_connections(settings: Settings | None = None) -> list[Connection]:
    _ensure_table(settings)
    with transaction(settings) as connection:
        rows = connection.execute("SELECT * FROM cloud_connections ORDER BY created_at").fetchall()
    return [_view(dict(row)) for row in rows]


def get_connection(connection_id: str, settings: Settings | None = None) -> Connection:
    for entry in list_connections(settings):
        if entry.id == connection_id:
            return entry
    raise LookupError(f"No cloud connection {connection_id}")


def create_connection(request: ConnectionRequest, settings: Settings | None = None) -> Connection:
    _check(request, request.secrets)
    _ensure_table(settings)
    connection_id = uuid.uuid4().hex[:12]
    fields = request.model_dump(exclude={"secrets"})
    with transaction(settings) as connection:
        connection.execute(
            "INSERT INTO cloud_connections (id, name, kind, endpoint, region, account, created_at)"
            " VALUES (:id, :name, :kind, :endpoint, :region, :account, :created_at)",
            {
                **fields,
                "id": connection_id,
                "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            },
        )
    _write_secrets(connection_id, request.secrets)
    return get_connection(connection_id, settings)


def update_connection(
    connection_id: str, request: ConnectionRequest, settings: Settings | None = None
) -> Connection:
    current = get_connection(connection_id, settings)
    if request.kind != current.kind:
        raise ValueError("A connection keeps its kind; add a new one instead.")
    _check(request, request.secrets)
    with transaction(settings) as connection:
        connection.execute(
            "UPDATE cloud_connections SET name = :name, endpoint = :endpoint, region = :region,"
            " account = :account WHERE id = :id",
            {**request.model_dump(exclude={"secrets", "kind"}), "id": connection_id},
        )
    _write_secrets(connection_id, request.secrets)
    return get_connection(connection_id, settings)


def delete_connection(connection_id: str, settings: Settings | None = None) -> None:
    current = get_connection(connection_id, settings)
    with transaction(settings) as connection:
        connection.execute("DELETE FROM cloud_connections WHERE id = ?", (connection_id,))
    for part in SECRETS[current.kind]:
        write_env_value(_key(connection_id, part), "")

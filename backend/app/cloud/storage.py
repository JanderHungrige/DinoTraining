"""One interface over S3, Azure Blob and Google Cloud Storage (doc 147), through `obstore`.

Five verbs: `list`, `get`, `put`, `put_if` (refused when someone else wrote in between)
and `head`. Docs 148-150 use only these, never the kind of store.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import obstore
from obstore.store import AzureStore, GCSStore, MemoryStore, S3Store

from app import __version__
from app.cloud.connections import Connection, secret, service_account_json
from app.cloud.errors import CloudError, explain

if TYPE_CHECKING:  # obstore declares its config dicts for type checkers only
    from obstore.store import AzureConfig, ClientConfig, GCSConfig, RetryConfig, S3Config

PAGE = 1000
USER_AGENT = f"V-Rex/{__version__}"


@dataclass(frozen=True)
class Entry:
    key: str
    size: int
    e_tag: str | None


class Storage:
    """A bucket (or container) and a prefix in it; keys are relative to the prefix."""

    def __init__(self, store: Any, where: str) -> None:
        self._store = store
        self.where = where

    def list(self, prefix: str = "") -> Iterator[list[Entry]]:
        """Pages of entries, so a million keys are never held at once."""
        try:
            for page in obstore.list(self._store, prefix=prefix or None, chunk_size=PAGE):
                yield [Entry(item["path"], int(item["size"]), item.get("e_tag")) for item in page]
        except Exception as error:  # noqa: BLE001 - every provider error becomes a CloudError
            raise explain(error, self.where) from error

    def get(self, key: str) -> bytes:
        try:
            return bytes(obstore.get(self._store, key).bytes())
        except Exception as error:  # noqa: BLE001
            raise explain(error, f"{self.where}/{key}") from error

    def get_range(self, key: str, length: int) -> bytes:
        """The first `length` bytes (all of them for a smaller file): a picture's header."""
        try:
            return bytes(obstore.get_range(self._store, key, start=0, length=length))
        except Exception as error:  # noqa: BLE001
            raise explain(error, f"{self.where}/{key}") from error

    def head(self, key: str) -> Entry | None:
        try:
            meta = obstore.head(self._store, key)
        except FileNotFoundError:
            return None
        except Exception as error:  # noqa: BLE001
            raise explain(error, f"{self.where}/{key}") from error
        return Entry(meta["path"], int(meta["size"]), meta.get("e_tag"))

    def put(self, key: str, data: bytes) -> str | None:
        """Write; returns the new ETag."""
        try:
            return obstore.put(self._store, key, data).get("e_tag")
        except Exception as error:  # noqa: BLE001
            raise explain(error, f"{self.where}/{key}") from error

    def put_if(self, key: str, data: bytes, e_tag: str | None) -> str | None:
        """Write only if the key is still `e_tag` (None: only if it does not exist yet)."""
        mode: Any = {"e_tag": e_tag} if e_tag else "create"
        try:
            return obstore.put(self._store, key, data, mode=mode).get("e_tag")
        except Exception as error:  # noqa: BLE001
            raise explain(error, f"{self.where}/{key}") from error


def _client_options(endpoint: str | None) -> ClientConfig:
    """Short connect timeout and a clear user agent; http only for an http:// endpoint."""
    options: ClientConfig = {"connect_timeout": "10s", "timeout": "120s", "user_agent": USER_AGENT}
    if endpoint and endpoint.startswith("http://"):
        options["allow_http"] = True
    return options


#: An unreachable endpoint fails in seconds, not after minutes of backing off.
RETRY: RetryConfig = {"max_retries": 2, "retry_timeout": timedelta(seconds=20)}


def open_storage(connection: Connection, bucket: str, prefix: str = "") -> Storage:
    """The store for a bucket (S3, GCS) or container (Azure) of this connection."""
    where = f"{bucket}/{prefix}".rstrip("/")
    prefix_arg = prefix.strip("/") or None
    options = _client_options(connection.endpoint)
    if connection.kind == "s3":
        config: S3Config = {
            "access_key_id": secret(connection.id, "access_key") or "",
            "secret_access_key": secret(connection.id, "secret_key") or "",
            "region": connection.region or "us-east-1",
        }
        if connection.endpoint:
            config["endpoint"] = connection.endpoint
        return Storage(
            S3Store(
                bucket, prefix=prefix_arg, config=config, client_options=options, retry_config=RETRY
            ),
            where,
        )
    if connection.kind == "azure":
        azure: AzureConfig = {"account_name": connection.account or ""}
        key, sas = secret(connection.id, "account_key"), secret(connection.id, "sas_token")
        if key:
            azure["account_key"] = key
        elif sas:
            azure["sas_key"] = sas.lstrip("?")
        if connection.endpoint:
            azure["endpoint"] = connection.endpoint
        return Storage(
            AzureStore(
                bucket, prefix=prefix_arg, config=azure, client_options=options, retry_config=RETRY
            ),
            where,
        )
    gcs: GCSConfig = {}
    key_json = service_account_json(connection.id)
    if key_json:
        gcs["service_account_key"] = key_json
    if connection.endpoint:
        gcs["base_url"] = connection.endpoint
    return Storage(
        GCSStore(bucket, prefix=prefix_arg, config=gcs, client_options=options, retry_config=RETRY),
        where,
    )


def memory_storage(where: str = "memory") -> Storage:
    """For tests: the same five verbs over obstore's in-memory store."""
    return Storage(MemoryStore(), where)


def probe_storage(storage: Storage) -> str:
    """List at most one key; the answer for "Test connection"."""
    for page in storage.list():
        return (
            f"Connected to {storage.where}: it holds files (for example {page[0].key})."
            if page
            else ""
        )
    return f"Connected to {storage.where}; it is empty."


__all__ = ["CloudError", "Entry", "Storage", "memory_storage", "open_storage", "probe_storage"]

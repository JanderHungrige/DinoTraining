"""The single shared SQLite connection module.

No other module calls ``sqlite3.connect``. Centralising it is what makes the PRAGMAs
below guaranteed rather than aspirational — foreign keys in particular are *off* by
default in SQLite, so a per-call connection would silently skip every cascade.
"""

from __future__ import annotations

import logging
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import Settings, get_settings
from app.core.paths import default_data_dir
from app.datasets.migrations import LATEST_VERSION, run_migrations
from app.datasets.schema import SCHEMA_SQL

logger = logging.getLogger(__name__)

#: Re-exported for callers that want the schema version. The authoritative value lives in
#: migrations.py and is written to ``PRAGMA user_version``; the constant that used to sit
#: here was never read by anything.
SCHEMA_VERSION = LATEST_VERSION

_lock = threading.Lock()
_connection: sqlite3.Connection | None = None
_connected_path: Path | None = None


def data_root(settings: Settings | None = None) -> Path:
    """Root directory for datasets and the index database."""
    settings = settings or get_settings()
    if settings.data_dir is not None:
        return settings.data_dir.expanduser().resolve()
    return (default_data_dir() / "data").resolve()


def database_path(settings: Settings | None = None) -> Path:
    return data_root(settings) / "dinotraining.db"


def _configure(connection: sqlite3.Connection) -> None:
    """PRAGMAs that must hold for every connection."""
    # Off by default in SQLite: without this the ON DELETE CASCADE clauses are decorative.
    connection.execute("PRAGMA foreign_keys = ON")
    # WAL lets the counter reads run while an annotation write is in flight.
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    connection.row_factory = sqlite3.Row


def get_connection(settings: Settings | None = None) -> sqlite3.Connection:
    """Return the process-wide connection, creating and migrating it on first use."""
    global _connection, _connected_path

    path = database_path(settings)
    with _lock:
        if _connection is not None and _connected_path == path:
            return _connection

        if _connection is not None:
            _connection.close()

        path.parent.mkdir(parents=True, exist_ok=True)
        # The connection is shared across FastAPI's threadpool workers; SQLite's own
        # locking covers the concurrency, so the per-thread check is not wanted here.
        connection = sqlite3.connect(str(path), check_same_thread=False)
        _configure(connection)
        connection.executescript(SCHEMA_SQL)
        connection.commit()
        # Creates what is missing above; this moves what already exists. Both are needed:
        # executescript cannot change a table that is already there. See migrations.py.
        version = run_migrations(connection)

        logger.info("SQLite index ready at %s (schema v%d)", path, version)
        _connection, _connected_path = connection, path
        return connection


@contextmanager
def transaction(settings: Settings | None = None) -> Iterator[sqlite3.Connection]:
    """Run a unit of work atomically. Rolls back on any exception."""
    connection = get_connection(settings)
    try:
        yield connection
    except Exception:
        connection.rollback()
        raise
    connection.commit()


def reset_connection() -> None:
    """Close the shared connection. For tests, and for changing the data directory."""
    global _connection, _connected_path
    with _lock:
        if _connection is not None:
            _connection.close()
        _connection, _connected_path = None, None

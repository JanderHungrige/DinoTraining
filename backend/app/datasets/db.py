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

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS datasets (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    prompt      TEXT,
    copy_images INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS images (
    id           INTEGER PRIMARY KEY,
    dataset_id   TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    path         TEXT NOT NULL,
    width        INTEGER NOT NULL,
    height       INTEGER NOT NULL,
    annotated_at TEXT NOT NULL,
    UNIQUE (dataset_id, path)
);

CREATE TABLE IF NOT EXISTS boxes (
    id         INTEGER PRIMARY KEY,
    image_id   INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    label      TEXT NOT NULL CHECK (label IN ('positive', 'negative', 'unclear')),
    provenance TEXT NOT NULL CHECK (provenance IN ('grounding-dino', 'hand-drawn')),
    prompt     TEXT,
    score      REAL,
    x          REAL NOT NULL,
    y          REAL NOT NULL,
    w          REAL NOT NULL CHECK (w > 0),
    h          REAL NOT NULL CHECK (h > 0)
);

-- Schema v2: trained, imported and default heads. Metadata here, weights on disk —
-- the same split datasets use, so "which heads do this task on this backbone" is a
-- SQL query rather than a directory walk that opens every weight file.
CREATE TABLE IF NOT EXISTS head_instances (
    id                   TEXT PRIMARY KEY,
    name                 TEXT NOT NULL,
    kind                 TEXT NOT NULL CHECK (
                             kind IN ('pretrained-default', 'community', 'trained-here')),
    head_type_id         TEXT NOT NULL,
    task                 TEXT NOT NULL,
    backbone_id          TEXT NOT NULL,
    backbone_family      TEXT NOT NULL,
    embed_dim            INTEGER NOT NULL,
    num_classes          INTEGER NOT NULL,
    -- JSON array. Order is load-bearing: index 3 in the weights means whatever index 3
    -- meant at training time, and nothing inside a tensor file records that.
    class_names          TEXT NOT NULL DEFAULT '[]',
    dataset_ids          TEXT NOT NULL DEFAULT '[]',
    metrics              TEXT NOT NULL DEFAULT '{}',
    primary_metric       TEXT,
    primary_metric_value REAL,
    config               TEXT NOT NULL DEFAULT '{}',
    source_repo          TEXT,
    source_digest        TEXT,
    epochs_trained       INTEGER NOT NULL DEFAULT 0,
    best_epoch           INTEGER,
    weights_path         TEXT NOT NULL,
    created_at           TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_images_dataset ON images(dataset_id);
CREATE INDEX IF NOT EXISTS idx_boxes_image    ON boxes(image_id);
CREATE INDEX IF NOT EXISTS idx_boxes_label    ON boxes(label);
CREATE INDEX IF NOT EXISTS idx_heads_task     ON head_instances(task);
CREATE INDEX IF NOT EXISTS idx_heads_backbone ON head_instances(backbone_id);
"""

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
        connection.executescript(_SCHEMA)
        connection.commit()

        logger.info("SQLite index ready at %s", path)
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

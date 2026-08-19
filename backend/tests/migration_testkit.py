"""The historical dataset schema, frozen, plus helpers for migration tests.

``LEGACY_SCHEMA`` is a copy of the Wave 1/2 DDL as it actually shipped. It must never be
"fixed" to match the current schema — it is the shape real installs are still sitting at,
and a migration test that starts from the *current* schema proves nothing.
"""

from __future__ import annotations

import sqlite3

# Frozen: the schema as shipped by Waves 1 and 2. Do not update.
LEGACY_SCHEMA = """
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


def _connect(script: str) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.executescript(script)
    connection.commit()
    return connection


def _legacy() -> sqlite3.Connection:
    """A Wave 1/2 database with one dataset, one image and one box already in it."""
    connection = _connect(LEGACY_SCHEMA)
    connection.execute(
        "INSERT INTO datasets (id, name, created_at, prompt, copy_images)"
        " VALUES ('d1', 'Cats', '2026-01-01T00:00:00+00:00', 'a cat', 0)"
    )
    connection.execute(
        "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
        " VALUES (1, 'd1', '/images/a.jpg', 200, 200, '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO boxes (image_id, label, provenance, prompt, score, x, y, w, h)"
        " VALUES (1, 'positive', 'grounding-dino', 'a cat', 0.9, 10, 10, 20, 20)"
    )
    connection.commit()
    return connection


def _version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    return {row["name"] for row in rows}

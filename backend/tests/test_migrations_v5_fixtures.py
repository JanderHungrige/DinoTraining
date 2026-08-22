"""A database at the v4 shape: masks present, provenance widened, no producer column."""

from __future__ import annotations

import sqlite3

from tests.migration_testkit import _connect

_V4_PROVENANCE = "'grounding-dino', 'hand-drawn', 'expert-head', 'sam3', 'grounded-sam'"

V4_SCHEMA = f"""
CREATE TABLE datasets (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,
    prompt TEXT, copy_images INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE images (
    id INTEGER PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    path TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL,
    annotated_at TEXT NOT NULL, UNIQUE (dataset_id, path)
);
CREATE TABLE boxes (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    label TEXT NOT NULL CHECK (label IN ('positive','negative','unclear')),
    provenance TEXT NOT NULL CHECK (provenance IN ({_V4_PROVENANCE})),
    prompt TEXT, score REAL,
    x REAL NOT NULL, y REAL NOT NULL,
    w REAL NOT NULL CHECK (w > 0), h REAL NOT NULL CHECK (h > 0)
);
CREATE TABLE masks (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    label TEXT NOT NULL CHECK (label IN ('positive','negative','unclear')),
    provenance TEXT NOT NULL CHECK (provenance IN ({_V4_PROVENANCE})),
    prompt TEXT, score REAL,
    rle_counts TEXT NOT NULL,
    rle_height INTEGER NOT NULL CHECK (rle_height > 0),
    rle_width INTEGER NOT NULL CHECK (rle_width > 0),
    x REAL NOT NULL, y REAL NOT NULL,
    w REAL NOT NULL CHECK (w > 0), h REAL NOT NULL CHECK (h > 0)
);
PRAGMA user_version = 4;
"""


def at_v4() -> sqlite3.Connection:
    connection = _connect(V4_SCHEMA)
    connection.execute(
        "INSERT INTO datasets (id, name, created_at, copy_images)"
        " VALUES ('d1', 'Cats', '2026-01-01T00:00:00+00:00', 0)"
    )
    connection.execute(
        "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
        " VALUES (1, 'd1', '/images/a.jpg', 4, 4, '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
        " VALUES (1, 'positive', 'grounding-dino', 1, 1, 2, 2)"
    )
    connection.commit()
    return connection

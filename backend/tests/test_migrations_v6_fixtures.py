"""A database at the v5 shape: masks, the Wave 4 provenances, and the producer column.

Frozen at what v5 actually shipped. It must never be updated to match the current schema —
it is the shape the developer's real install is sitting at, and that is the only place a
missing migration can bite.
"""

from __future__ import annotations

import sqlite3

from tests.migration_testkit import _connect

_V5_PROVENANCE = "'grounding-dino', 'hand-drawn', 'expert-head', 'sam3', 'grounded-sam'"

V5_SCHEMA = f"""
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
    provenance TEXT NOT NULL CHECK (provenance IN ({_V5_PROVENANCE})),
    prompt TEXT, score REAL, producer TEXT,
    x REAL NOT NULL, y REAL NOT NULL,
    w REAL NOT NULL CHECK (w > 0), h REAL NOT NULL CHECK (h > 0)
);
CREATE TABLE masks (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    label TEXT NOT NULL CHECK (label IN ('positive','negative','unclear')),
    provenance TEXT NOT NULL CHECK (provenance IN ({_V5_PROVENANCE})),
    prompt TEXT, score REAL, producer TEXT,
    rle_counts TEXT NOT NULL,
    rle_height INTEGER NOT NULL CHECK (rle_height > 0),
    rle_width INTEGER NOT NULL CHECK (rle_width > 0),
    x REAL NOT NULL, y REAL NOT NULL,
    w REAL NOT NULL CHECK (w > 0), h REAL NOT NULL CHECK (h > 0)
);
PRAGMA user_version = 5;
"""


def at_v5() -> sqlite3.Connection:
    """A v5 database with one dataset, one image, one box and one mask already in it."""
    connection = _connect(V5_SCHEMA)
    connection.execute(
        "INSERT INTO datasets (id, name, created_at, copy_images)"
        " VALUES ('d1', 'Cats', '2026-01-01T00:00:00+00:00', 0)"
    )
    connection.execute(
        "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
        " VALUES (1, 'd1', '/images/a.jpg', 4, 4, '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO boxes (image_id, label, provenance, prompt, x, y, w, h)"
        " VALUES (1, 'positive', 'grounding-dino', 'a cat', 1, 1, 2, 2)"
    )
    connection.execute(
        "INSERT INTO masks"
        " (image_id, label, provenance, rle_counts, rle_height, rle_width, x, y, w, h)"
        " VALUES (1, 'positive', 'grounded-sam', '[0,16]', 4, 4, 0, 0, 4, 4)"
    )
    connection.commit()
    return connection

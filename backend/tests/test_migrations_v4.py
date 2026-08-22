"""v3 -> v4: the incremental upgrade, and the one that generalised the runner.

A v3 database already has a `masks` table, so this step is not "create what is missing" —
it is "rebuild every table whose provenance CHECK is out of date". Both `boxes` and `masks`
carry that CHECK, and a runner that rebuilt only `boxes` would leave mask inserts failing on
exactly the installs that had already upgraded once. That is the regression these tests pin.
"""

from __future__ import annotations

import sqlite3

from app.datasets.migrations import LATEST_VERSION, run_migrations
from tests.migration_testkit import _connect

# Frozen: the provenance set as it stood at v3, before `grounded-sam` was added.
_V3_PROVENANCE = "'grounding-dino', 'hand-drawn', 'expert-head', 'sam3'"

V3_SCHEMA = f"""
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
    provenance TEXT NOT NULL CHECK (provenance IN ({_V3_PROVENANCE})),
    prompt TEXT, score REAL,
    x REAL NOT NULL, y REAL NOT NULL,
    w REAL NOT NULL CHECK (w > 0), h REAL NOT NULL CHECK (h > 0)
);
CREATE TABLE masks (
    id INTEGER PRIMARY KEY,
    image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    label TEXT NOT NULL CHECK (label IN ('positive','negative','unclear')),
    provenance TEXT NOT NULL CHECK (provenance IN ({_V3_PROVENANCE})),
    prompt TEXT, score REAL,
    rle_counts TEXT NOT NULL,
    rle_height INTEGER NOT NULL CHECK (rle_height > 0),
    rle_width INTEGER NOT NULL CHECK (rle_width > 0),
    x REAL NOT NULL, y REAL NOT NULL,
    w REAL NOT NULL CHECK (w > 0), h REAL NOT NULL CHECK (h > 0)
);
CREATE INDEX idx_boxes_image ON boxes(image_id);
CREATE INDEX idx_boxes_label ON boxes(label);
CREATE INDEX idx_masks_image ON masks(image_id);
CREATE INDEX idx_masks_label ON masks(label);
PRAGMA user_version = 3;
"""


def _at_v3() -> sqlite3.Connection:
    """A v3 database with one box and one mask already stored."""
    connection = _connect(V3_SCHEMA)
    connection.execute(
        "INSERT INTO datasets (id, name, created_at, prompt, copy_images)"
        " VALUES ('d1', 'Cats', '2026-01-01T00:00:00+00:00', 'a cat', 0)"
    )
    connection.execute(
        "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
        " VALUES (1, 'd1', '/images/a.jpg', 4, 4, '2026-01-01T00:00:00+00:00')"
    )
    connection.execute(
        "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
        " VALUES (1, 'positive', 'sam3', 1, 1, 2, 2)"
    )
    connection.execute(
        "INSERT INTO masks (image_id, label, provenance, prompt, score, rle_counts,"
        " rle_height, rle_width, x, y, w, h)"
        " VALUES (1, 'positive', 'sam3', 'a cat', 0.8, '[5,2,2,2,5]', 4, 4, 1, 1, 2, 2)"
    )
    connection.commit()
    return connection


def _version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _assert_row_preserved(table: str) -> None:
    """Every pre-existing value survives, compared column by column.

    Not whole-row equality: a migration may legitimately *add* a nullable column, and
    asserting the row is byte-identical would fail on exactly the change being tested
    while saying nothing about whether the old data survived.
    """
    connection = _at_v3()
    before = dict(connection.execute(f"SELECT * FROM {table}").fetchone())  # noqa: S608
    run_migrations(connection)
    after = dict(connection.execute(f"SELECT * FROM {table}").fetchone())  # noqa: S608

    for column, value in before.items():
        assert after[column] == value, f"{table}.{column} changed during the rebuild"
    assert set(after) >= set(before), "a column disappeared during the rebuild"


class TestIncrementalUpgrade:
    def test_boxes_gains_the_new_provenance(self) -> None:
        connection = _at_v3()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'grounded-sam', 1, 1, 2, 2)"
        )
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 2

    def test_masks_gains_the_new_provenance(self) -> None:
        """The table a boxes-only runner would have missed."""
        connection = _at_v3()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO masks (image_id, label, provenance, rle_counts,"
            " rle_height, rle_width, x, y, w, h)"
            " VALUES (1, 'positive', 'grounded-sam', '[5,2,2,2,5]', 4, 4, 1, 1, 2, 2)"
        )
        assert connection.execute("SELECT COUNT(*) FROM masks").fetchone()[0] == 2

    def test_existing_mask_rows_survive_the_rebuild(self) -> None:
        _assert_row_preserved("masks")

    def test_existing_box_rows_survive_the_rebuild(self) -> None:
        _assert_row_preserved("boxes")

    def test_it_stamps_the_latest_version(self) -> None:
        connection = _at_v3()
        run_migrations(connection)
        assert _version(connection) == LATEST_VERSION

    def test_mask_indexes_are_recreated(self) -> None:
        connection = _at_v3()
        run_migrations(connection)
        names = {
            row["name"]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='masks'"
            )
        }
        assert {"idx_masks_image", "idx_masks_label"} <= names

    def test_mask_cascade_survives_the_rebuild(self) -> None:
        connection = _at_v3()
        run_migrations(connection)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM images WHERE id = 1")
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM masks").fetchone()[0] == 0

    def test_a_value_outside_the_widened_set_is_still_rejected(self) -> None:
        connection = _at_v3()
        run_migrations(connection)
        try:
            connection.execute(
                "INSERT INTO masks (image_id, label, provenance, rle_counts,"
                " rle_height, rle_width, x, y, w, h)"
                " VALUES (1, 'positive', 'bogus', '[5,2,2,2,5]', 4, 4, 1, 1, 2, 2)"
            )
        except sqlite3.IntegrityError:
            return
        raise AssertionError("widening must not become 'no constraint at all'")

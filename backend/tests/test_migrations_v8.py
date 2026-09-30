"""v8: `images.sequence` and `images.frame_index` for frames of a video or folder (doc 73).

Found in the running app, not by a test: every test built a fresh database, where
schema.py already has the columns, while the developer's install was stamped 7 and
`run_migrations` returned before looking. The listing then failed with "no such column:
sequence" as a 500. Doc 22's bug, fourth time. So this pins both halves: a v7 database
gains the columns, and **an install already stamped latest but missing a column gains it
too**, because the added-column check no longer hides behind the version gate.
"""

from __future__ import annotations

import sqlite3

from app.datasets.migrations import LATEST_VERSION, run_migrations
from tests.migration_testkit import _version
from tests.test_migrations_v7_fixtures import at_v6


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def test_the_version_moved() -> None:
    assert LATEST_VERSION >= 8


def test_an_older_database_gains_the_sequence_columns() -> None:
    connection = at_v6()
    assert "sequence" not in _columns(connection, "images")
    run_migrations(connection)
    assert {"sequence", "frame_index"} <= _columns(connection, "images")
    assert _version(connection) == LATEST_VERSION


def test_a_database_stamped_latest_but_missing_a_column_still_gets_it() -> None:
    connection = at_v6()
    connection.execute(f"PRAGMA user_version = {LATEST_VERSION}")
    run_migrations(connection)
    assert {"sequence", "frame_index"} <= _columns(connection, "images")


def test_existing_images_keep_their_rows_with_no_position() -> None:
    connection = at_v6()
    run_migrations(connection)
    row = connection.execute("SELECT path, sequence, frame_index FROM images").fetchone()
    assert row["path"] == "/images/a.jpg"
    assert row["sequence"] is None
    assert row["frame_index"] is None

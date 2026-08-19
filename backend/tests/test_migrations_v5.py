"""v5: adding a nullable column.

A different shape of migration from v3/v4 and worth its own tests. SQLite refuses to alter
a CHECK constraint but will happily append a nullable column, so this is an ALTER rather
than a rebuild — cheaper, and it must not disturb the rows already there.

The trap it guards: a rebuild triggered on an *older* database would try to copy the new
column out of a table that does not have it, failing with "no such column" in the middle of
a migration. `_rebuild_table` therefore intersects its column list with what the source
actually has.
"""

from __future__ import annotations

import sqlite3

from app.datasets.migrations import LATEST_VERSION, run_migrations
from app.datasets.schema import ADDED_COLUMNS, SCHEMA_SQL
from tests.migration_testkit import _connect
from tests.test_migrations_v5_fixtures import at_v4


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


class TestColumnAddition:
    def test_producer_is_added_to_boxes(self) -> None:
        connection = at_v4()
        assert "producer" not in _columns(connection, "boxes")
        run_migrations(connection)
        assert "producer" in _columns(connection, "boxes")

    def test_producer_is_added_to_masks(self) -> None:
        connection = at_v4()
        run_migrations(connection)
        assert "producer" in _columns(connection, "masks")

    def test_existing_rows_gain_a_null_producer_rather_than_being_dropped(self) -> None:
        connection = at_v4()
        run_migrations(connection)
        row = connection.execute("SELECT provenance, producer FROM boxes").fetchone()
        assert row["provenance"] == "grounding-dino"
        assert row["producer"] is None

    def test_a_producer_can_be_written_after_the_upgrade(self) -> None:
        connection = at_v4()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, producer, x, y, w, h)"
            " VALUES (1, 'positive', 'expert-head',"
            " '{\"id\":\"h1\",\"label\":\"Bolt\"}', 1, 1, 2, 2)"
        )
        stored = connection.execute(
            "SELECT producer FROM boxes WHERE provenance = 'expert-head'"
        ).fetchone()["producer"]
        assert "Bolt" in stored

    def test_it_stamps_the_latest_version(self) -> None:
        connection = at_v4()
        run_migrations(connection)
        assert int(connection.execute("PRAGMA user_version").fetchone()[0]) == LATEST_VERSION

    def test_running_twice_does_not_duplicate_the_column(self) -> None:
        connection = at_v4()
        run_migrations(connection)
        run_migrations(connection)
        columns = [row[1] for row in connection.execute("PRAGMA table_info(boxes)")]
        assert columns.count("producer") == 1

    def test_a_fresh_database_already_has_every_added_column(self) -> None:
        """schema.py and ADDED_COLUMNS must not drift: a fresh install skips the ALTER."""
        connection = _connect(SCHEMA_SQL)
        run_migrations(connection)
        for table, columns in ADDED_COLUMNS.items():
            assert set(columns) <= _columns(connection, table), table

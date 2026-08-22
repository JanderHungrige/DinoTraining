"""v6: widening the provenance CHECK for `imported`.

The same rebuild v3 and v4 exercised, but this file exists for one reason the earlier ones
cannot cover: **the version gate**. `run_migrations` returns early once the stored version
reaches `LATEST_VERSION`, so a database stamped 5 only rebuilds because 5 < 6. Had the
constant been left at 5 while `PROVENANCE_VALUES` grew, every test that builds a fresh
database would still pass — schema.py writes the current CHECK — and the developer's real
install would raise IntegrityError on the first import. That is doc 22's bug, and the test
that catches it has to start from a *stamped* older database, not a bare one.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.datasets.migrations import LATEST_VERSION, run_migrations
from app.datasets.schema import PROVENANCE_VALUES
from tests.migration_testkit import _version
from tests.test_migrations_v6_fixtures import at_v5


def _insert_imported_box(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO boxes (image_id, label, provenance, prompt, x, y, w, h)"
        " VALUES (1, 'positive', 'imported', 'dog', 0, 0, 1, 1)"
    )


class TestTheVersionGate:
    def test_a_v5_database_is_below_the_latest_version(self) -> None:
        # If this ever fails, the constant was not bumped and every test below is vacuous.
        assert LATEST_VERSION > 5
        assert _version(at_v5()) < LATEST_VERSION

    def test_imported_is_rejected_before_migrating(self) -> None:
        connection = at_v5()
        with pytest.raises(sqlite3.IntegrityError):
            _insert_imported_box(connection)

    def test_imported_is_accepted_after_migrating(self) -> None:
        connection = at_v5()
        run_migrations(connection)
        _insert_imported_box(connection)
        stored = connection.execute(
            "SELECT provenance, prompt FROM boxes WHERE provenance = 'imported'"
        ).fetchone()
        assert stored["provenance"] == "imported"
        assert stored["prompt"] == "dog"

    def test_version_is_stamped(self) -> None:
        connection = at_v5()
        assert run_migrations(connection) == LATEST_VERSION
        assert _version(connection) == LATEST_VERSION


class TestTheRebuildKeepsEverything:
    def test_existing_boxes_survive(self) -> None:
        connection = at_v5()
        run_migrations(connection)
        row = connection.execute(
            "SELECT provenance, prompt, x, y, w, h FROM boxes"
        ).fetchone()
        assert row["provenance"] == "grounding-dino"
        assert row["prompt"] == "a cat"
        assert (row["x"], row["y"], row["w"], row["h"]) == (1, 1, 2, 2)

    def test_existing_masks_survive(self) -> None:
        connection = at_v5()
        run_migrations(connection)
        row = connection.execute("SELECT provenance, rle_counts FROM masks").fetchone()
        assert row["provenance"] == "grounded-sam"
        assert row["rle_counts"] == "[0,16]"

    def test_the_producer_column_is_not_lost(self) -> None:
        # A rebuild carries a fixed column list; dropping `producer` would silently
        # discard Wave 4's traceability on every existing install.
        connection = at_v5()
        run_migrations(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(boxes)")}
        assert "producer" in columns

    def test_masks_are_widened_too(self) -> None:
        connection = at_v5()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO masks"
            " (image_id, label, provenance, rle_counts, rle_height, rle_width, x, y, w, h)"
            " VALUES (1, 'positive', 'imported', '[0,16]', 4, 4, 0, 0, 4, 4)"
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM masks WHERE provenance = 'imported'"
        ).fetchone()[0] == 1

    def test_foreign_keys_still_cascade(self) -> None:
        connection = at_v5()
        run_migrations(connection)
        connection.execute("DELETE FROM images WHERE id = 1")
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 0

    def test_rerunning_is_a_no_op(self) -> None:
        connection = at_v5()
        run_migrations(connection)
        before = connection.execute("SELECT id, rowid FROM boxes").fetchall()
        run_migrations(connection)
        after = connection.execute("SELECT id, rowid FROM boxes").fetchall()
        assert [tuple(row) for row in before] == [tuple(row) for row in after]


class TestTheVocabulary:
    def test_imported_is_in_the_schema_vocabulary(self) -> None:
        assert "imported" in PROVENANCE_VALUES

    def test_every_value_reaches_the_rebuilt_check(self) -> None:
        connection = at_v5()
        run_migrations(connection)
        ddl = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='boxes'"
        ).fetchone()[0]
        for value in PROVENANCE_VALUES:
            assert f"'{value}'" in ddl

"""v7: widening the provenance CHECK for `foundation-model`.

The same shape as v6, and it exists for the same one reason: **the version gate**.
`run_migrations` returns early once the stored version reaches `LATEST_VERSION`, so a
database stamped 6 only rebuilds because 6 < 7. Leave the constant behind and every test
still passes — schema.py writes the current CHECK on a fresh database — while the
developer's real install raises IntegrityError the first time a foundation model proposes
a box that gets saved. Doc 22's bug, third time of asking.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.datasets.migrations import LATEST_VERSION, run_migrations
from app.datasets.schema import PROVENANCE_VALUES
from tests.migration_testkit import _version
from tests.test_migrations_v7_fixtures import at_v6


def _insert_foundation_box(connection: sqlite3.Connection) -> None:
    connection.execute(
        "INSERT INTO boxes (image_id, label, provenance, prompt, x, y, w, h)"
        " VALUES (1, 'positive', 'foundation-model', 'cat', 0, 0, 1, 1)"
    )


class TestTheVersionGate:
    def test_a_v6_database_is_below_the_latest_version(self) -> None:
        assert LATEST_VERSION > 6
        assert _version(at_v6()) < LATEST_VERSION

    def test_foundation_model_is_rejected_before_migrating(self) -> None:
        with pytest.raises(sqlite3.IntegrityError):
            _insert_foundation_box(at_v6())

    def test_it_is_accepted_after_migrating(self) -> None:
        connection = at_v6()
        run_migrations(connection)
        _insert_foundation_box(connection)
        row = connection.execute(
            "SELECT provenance, prompt FROM boxes WHERE provenance = 'foundation-model'"
        ).fetchone()
        assert row["provenance"] == "foundation-model"
        assert row["prompt"] == "cat"

    def test_version_is_stamped(self) -> None:
        connection = at_v6()
        assert run_migrations(connection) == LATEST_VERSION
        assert _version(connection) == LATEST_VERSION


class TestTheRebuildKeepsEverything:
    def test_the_imported_provenance_from_v6_still_works(self) -> None:
        """A rebuild that narrowed the CHECK would break the previous wave's data."""
        connection = at_v6()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'imported', 0, 0, 1, 1)"
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM boxes WHERE provenance = 'imported'"
        ).fetchone()[0] == 1

    def test_existing_rows_survive(self) -> None:
        connection = at_v6()
        run_migrations(connection)
        row = connection.execute("SELECT provenance, prompt FROM boxes").fetchone()
        assert row["provenance"] == "grounding-dino"
        assert row["prompt"] == "a cat"

    def test_the_producer_column_is_not_lost(self) -> None:
        connection = at_v6()
        run_migrations(connection)
        columns = {row[1] for row in connection.execute("PRAGMA table_info(boxes)")}
        assert "producer" in columns

    def test_rerunning_is_a_no_op(self) -> None:
        connection = at_v6()
        run_migrations(connection)
        before = connection.execute("SELECT id, rowid FROM boxes").fetchall()
        run_migrations(connection)
        after = connection.execute("SELECT id, rowid FROM boxes").fetchall()
        assert [tuple(r) for r in before] == [tuple(r) for r in after]


class TestTheVocabulary:
    def test_every_value_reaches_the_rebuilt_check(self) -> None:
        connection = at_v6()
        run_migrations(connection)
        ddl = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='boxes'"
        ).fetchone()[0]
        for value in PROVENANCE_VALUES:
            assert f"'{value}'" in ddl

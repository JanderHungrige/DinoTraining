"""Tests for the schema migration runner.

The point of this file is the *upgrade* path. A test that only builds a fresh database
proves nothing about a change to an existing table: SQLite's ``CREATE TABLE IF NOT EXISTS``
is a no-op against a table that already exists, so a widened CHECK constraint silently does
not apply to any database that predates it. Every test here that matters therefore starts
from the historical schema, not from ``schema.py``.
"""

from __future__ import annotations

import sqlite3

import pytest

from app.datasets.migrations import LATEST_VERSION, run_migrations
from app.datasets.schema import PROVENANCE_VALUES, SCHEMA_SQL
from tests.migration_testkit import _connect, _legacy, _tables, _version


class TestUpgradeFromLegacy:
    """The path a real install takes. These are the tests that catch the actual bug."""

    def test_widened_provenance_accepts_expert_head_on_an_existing_database(self) -> None:
        connection = _legacy()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'expert-head', 1, 1, 5, 5)"
        )
        stored = connection.execute(
            "SELECT provenance FROM boxes WHERE provenance = 'expert-head'"
        ).fetchone()
        assert stored is not None

    def test_widened_provenance_accepts_sam3_on_an_existing_database(self) -> None:
        connection = _legacy()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'sam3', 1, 1, 5, 5)"
        )
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 2

    def test_the_rebuild_still_rejects_a_value_outside_the_widened_set(self) -> None:
        """Widening must not become 'no constraint at all'."""
        connection = _legacy()
        run_migrations(connection)
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
                " VALUES (1, 'positive', 'not-a-real-source', 1, 1, 5, 5)"
            )

    def test_existing_rows_survive_the_table_rebuild(self) -> None:
        connection = _legacy()
        run_migrations(connection)
        row = connection.execute(
            "SELECT image_id, label, provenance, prompt, score, x, y, w, h FROM boxes"
        ).fetchone()
        assert row["image_id"] == 1
        assert (row["label"], row["provenance"]) == ("positive", "grounding-dino")
        assert (row["prompt"], row["score"]) == ("a cat", 0.9)
        assert (row["x"], row["y"], row["w"], row["h"]) == (10.0, 10.0, 20.0, 20.0)

    def test_the_masks_table_is_added(self) -> None:
        connection = _legacy()
        run_migrations(connection)
        assert "masks" in _tables(connection)

    def test_foreign_keys_still_cascade_after_the_rebuild(self) -> None:
        """A rebuild that loses the REFERENCES clause leaves orphan rows behind."""
        connection = _legacy()
        run_migrations(connection)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("DELETE FROM images WHERE id = 1")
        connection.commit()
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 0

    def test_box_indexes_are_recreated(self) -> None:
        connection = _legacy()
        run_migrations(connection)
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='boxes'"
        ).fetchall()
        names = {row["name"] for row in rows}
        assert {"idx_boxes_image", "idx_boxes_label"} <= names

    def test_it_stamps_the_version(self) -> None:
        connection = _legacy()
        run_migrations(connection)
        assert _version(connection) == LATEST_VERSION


class TestTheRealCallOrder:
    """``get_connection`` applies schema.py and *then* migrates. Reproduce that exactly.

    Calling ``run_migrations`` on a bare legacy connection — as the tests above do — misses
    a whole class of bug: ``executescript(SCHEMA_SQL)`` creates every missing table first, so
    any freshness probe of the form "does table X exist" is already satisfied before the
    runner is asked to decide. A probe like that skips the migration for every real install
    while the rest of this file stays green. That shipped once; these tests are why it did
    not ship twice.
    """

    def _open_like_production(self) -> sqlite3.Connection:
        connection = _legacy()
        connection.executescript(SCHEMA_SQL)  # exactly what get_connection does first
        connection.commit()
        run_migrations(connection)
        return connection

    def test_the_constraint_is_widened_despite_schema_being_applied_first(self) -> None:
        connection = self._open_like_production()
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'expert-head', 1, 1, 5, 5)"
        )
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 2

    def test_the_stored_ddl_carries_every_current_provenance_value(self) -> None:
        connection = self._open_like_production()
        ddl = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='boxes'"
        ).fetchone()["sql"]
        for value in PROVENANCE_VALUES:
            assert value in ddl, f"{value} missing from the migrated boxes constraint"

    def test_existing_rows_survive_the_production_open_path(self) -> None:
        connection = self._open_like_production()
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 1

    def test_masks_can_be_written_after_the_production_open_path(self) -> None:
        connection = self._open_like_production()
        connection.execute(
            "INSERT INTO masks (image_id, label, provenance, rle_counts,"
            " rle_height, rle_width, x, y, w, h)"
            " VALUES (1, 'positive', 'sam3', '[5,2,2,2,5]', 4, 4, 1, 1, 2, 2)"
        )
        assert connection.execute("SELECT COUNT(*) FROM masks").fetchone()[0] == 1


class TestTheTrapThisRunnerExistsFor:
    """Pins the SQLite behaviour that makes a table rebuild mandatory.

    If someone later "simplifies" run_migrations back to executing schema.py, these two
    tests fail — which is the whole point of keeping them.
    """

    def test_applying_the_new_schema_alone_does_not_widen_the_constraint(self) -> None:
        connection = _legacy()
        connection.executescript(SCHEMA_SQL)  # the naive "migration"
        connection.commit()
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            connection.execute(
                "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
                " VALUES (1, 'positive', 'expert-head', 1, 1, 5, 5)"
            )

    def test_the_stored_ddl_still_shows_the_old_constraint_after_a_naive_apply(self) -> None:
        connection = _legacy()
        connection.executescript(SCHEMA_SQL)
        ddl = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name='boxes'"
        ).fetchone()["sql"]
        assert "expert-head" not in ddl


class TestFreshDatabase:
    def test_a_fresh_database_is_stamped_without_replaying_migrations(self) -> None:
        connection = _connect(SCHEMA_SQL)
        run_migrations(connection)
        assert _version(connection) == LATEST_VERSION

    def test_a_fresh_database_accepts_the_new_provenance_values(self) -> None:
        connection = _connect(SCHEMA_SQL)
        run_migrations(connection)
        connection.execute(
            "INSERT INTO datasets (id, name, created_at, copy_images)"
            " VALUES ('d1', 'C', '2026-01-01T00:00:00+00:00', 0)"
        )
        connection.execute(
            "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
            " VALUES (1, 'd1', '/a.jpg', 10, 10, '2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'sam3', 1, 1, 5, 5)"
        )
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 1


class TestIdempotence:
    def test_running_twice_changes_nothing(self) -> None:
        connection = _legacy()
        run_migrations(connection)
        first = connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0]
        run_migrations(connection)
        assert _version(connection) == LATEST_VERSION
        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == first

    def test_a_second_run_does_not_rebuild_an_already_current_table(self) -> None:
        """Re-running must be cheap and must not churn rowids."""
        connection = _legacy()
        run_migrations(connection)
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'sam3', 1, 1, 5, 5)"
        )
        connection.commit()
        before = [row["id"] for row in connection.execute("SELECT id FROM boxes ORDER BY id")]
        run_migrations(connection)
        after = [row["id"] for row in connection.execute("SELECT id FROM boxes ORDER BY id")]
        assert before == after

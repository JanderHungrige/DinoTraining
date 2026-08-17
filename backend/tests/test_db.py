"""Tests for the shared SQLite connection module."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from app.core.config import Settings
from app.datasets.db import database_path, get_connection, reset_connection, transaction


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[Settings]:
    reset_connection()
    yield Settings(_env_file=None, data_dir=tmp_path)
    reset_connection()


class TestConnection:
    def test_creates_the_database_file(self, settings: Settings, tmp_path: Path) -> None:
        get_connection(settings)
        assert database_path(settings).is_file()

    def test_returns_the_same_connection(self, settings: Settings) -> None:
        assert get_connection(settings) is get_connection(settings)

    def test_foreign_keys_are_enforced(self, settings: Settings) -> None:
        """Off by default in SQLite — without the PRAGMA the cascades are decorative."""
        connection = get_connection(settings)
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1

    def test_rows_are_addressable_by_name(self, settings: Settings) -> None:
        connection = get_connection(settings)
        row = connection.execute("SELECT 1 AS answer").fetchone()
        assert row["answer"] == 1

    def test_schema_creates_every_table(self, settings: Settings) -> None:
        connection = get_connection(settings)
        names = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        assert {"datasets", "images", "boxes"} <= names


class TestConstraints:
    def test_invalid_label_is_rejected(self, settings: Settings) -> None:
        connection = get_connection(settings)
        connection.execute(
            "INSERT INTO datasets (id, name, created_at) VALUES ('d', 'n', 'now')"
        )
        connection.execute(
            "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
            " VALUES (1, 'd', 'a.jpg', 10, 10, 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
                " VALUES (1, 'maybe', 'hand-drawn', 0, 0, 1, 1)"
            )

    def test_zero_area_box_is_rejected(self, settings: Settings) -> None:
        connection = get_connection(settings)
        connection.execute(
            "INSERT INTO datasets (id, name, created_at) VALUES ('d', 'n', 'now')"
        )
        connection.execute(
            "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
            " VALUES (1, 'd', 'a.jpg', 10, 10, 'now')"
        )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
                " VALUES (1, 'positive', 'hand-drawn', 0, 0, 0, 5)"
            )

    def test_deleting_a_dataset_cascades_to_boxes(self, settings: Settings) -> None:
        connection = get_connection(settings)
        connection.execute(
            "INSERT INTO datasets (id, name, created_at) VALUES ('d', 'n', 'now')"
        )
        connection.execute(
            "INSERT INTO images (id, dataset_id, path, width, height, annotated_at)"
            " VALUES (1, 'd', 'a.jpg', 10, 10, 'now')"
        )
        connection.execute(
            "INSERT INTO boxes (image_id, label, provenance, x, y, w, h)"
            " VALUES (1, 'positive', 'hand-drawn', 0, 0, 5, 5)"
        )
        connection.commit()

        connection.execute("DELETE FROM datasets WHERE id = 'd'")
        connection.commit()

        assert connection.execute("SELECT COUNT(*) FROM boxes").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM images").fetchone()[0] == 0


class TestTransaction:
    def test_rolls_back_on_error(self, settings: Settings) -> None:
        with pytest.raises(RuntimeError):
            with transaction(settings) as connection:
                connection.execute(
                    "INSERT INTO datasets (id, name, created_at) VALUES ('x', 'n', 'now')"
                )
                raise RuntimeError("boom")

        connection = get_connection(settings)
        assert connection.execute("SELECT COUNT(*) FROM datasets").fetchone()[0] == 0

    def test_commits_on_success(self, settings: Settings) -> None:
        with transaction(settings) as connection:
            connection.execute(
                "INSERT INTO datasets (id, name, created_at) VALUES ('x', 'n', 'now')"
            )
        assert get_connection(settings).execute(
            "SELECT COUNT(*) FROM datasets"
        ).fetchone()[0] == 1

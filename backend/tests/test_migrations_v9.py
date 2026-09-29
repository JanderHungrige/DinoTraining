"""v9: images.split and images.excluded (docs 83, 84), on an existing install."""

from __future__ import annotations

from app.datasets.migrations import LATEST_VERSION, run_migrations
from tests.test_migrations_v7_fixtures import at_v6


def _columns(connection) -> set[str]:  # type: ignore[no-untyped-def]
    return {row[1] for row in connection.execute("PRAGMA table_info(images)")}


def test_the_version_moved() -> None:
    assert LATEST_VERSION >= 9


def test_an_older_database_gains_split_and_excluded() -> None:
    connection = at_v6()
    run_migrations(connection)
    assert {"split", "excluded"} <= _columns(connection)
    row = connection.execute("SELECT split, excluded FROM images").fetchone()
    assert row["split"] is None
    assert row["excluded"] is None

"""Schema migrations.

``CREATE TABLE IF NOT EXISTS`` creates tables that are missing and does **nothing** to tables
that already exist. That was sufficient while every schema change added a table — Wave 2's
``head_instances`` migrated existing installs correctly for exactly that reason. It is not
sufficient once a change modifies an existing table, because a widened CHECK constraint then
applies only to databases created after the change.

The failure mode is the dangerous kind: every test builds a fresh database and passes, while
a real install — which is the only place an *old* table exists — raises ``IntegrityError`` at
runtime. ``test_migrations.py`` therefore starts from a frozen copy of the historical DDL.

``PRAGMA user_version`` is the version marker. The ``SCHEMA_VERSION`` constant that used to
sit in ``db.py`` was never read by anything; it recorded an intention that was not
implemented.

**Steps decide for themselves whether they have work to do, by inspecting the DDL SQLite
actually stored.** They do not trust the version stamp and they do not probe for the
existence of some other table: ``get_connection`` applies ``schema.py`` *before* calling
here, so any "does table X exist" signal is already true by the time the runner is consulted.
A probe like that silently skips the migration for every real install. That happened once.
"""

from __future__ import annotations

import logging
import sqlite3

from app.datasets.schema import (
    ADDED_COLUMNS,
    BOX_INDEXES,
    BOXES_TABLE,
    MASK_INDEXES,
    MASKS_TABLE,
    PROVENANCE_TABLES,
    PROVENANCE_VALUES,
)

logger = logging.getLogger(__name__)

#: v3 added masks and the expert-head/sam3 provenances; v4 added grounded-sam;
#: v5 added the producer column; v6 added the imported provenance.
#:
#: Bumping this is **not** bookkeeping. `run_migrations` returns early once the stored
#: version reaches it, so widening PROVENANCE_VALUES without moving this number rebuilds
#: the CHECK on fresh databases only — every test passes and the real install raises
#: IntegrityError on first write. The rebuild itself needs no new code; the gate does.
LATEST_VERSION = 6

# Columns carried across a rebuild, per table, in a fixed order so the INSERT..SELECT cannot
# silently transpose two same-typed columns if a schema is ever reordered.
_CARRIED_COLUMNS: dict[str, str] = {
    "boxes": "image_id, label, provenance, prompt, score, producer, x, y, w, h",
    "masks": (
        "image_id, label, provenance, prompt, score, producer,"
        " rle_counts, rle_height, rle_width, x, y, w, h"
    ),
}

_TABLE_DDL: dict[str, str] = {"boxes": BOXES_TABLE, "masks": MASKS_TABLE}
_TABLE_INDEXES: dict[str, str] = {"boxes": BOX_INDEXES, "masks": MASK_INDEXES}


def run_migrations(connection: sqlite3.Connection) -> int:
    """Bring ``connection`` up to ``LATEST_VERSION``. Returns the resulting version.

    Idempotent: a database already at the latest shape is left untouched, including its
    rowids — a re-run must not churn a table.
    """
    if _current_version(connection) >= LATEST_VERSION:
        return LATEST_VERSION

    missing = [t for t in PROVENANCE_TABLES if _stored_ddl(connection, t) is None]
    stale = [t for t in PROVENANCE_TABLES if _provenance_is_stale(connection, t)]

    if missing or stale or _columns_are_missing(connection):
        logger.info(
            "Migrating dataset schema to version %d%s%s",
            LATEST_VERSION,
            f" (creating {', '.join(missing)})" if missing else "",
            f" (rebuilding {', '.join(stale)})" if stale else "",
        )
        # Creating is separate from rebuilding so that run_migrations is correct on its own,
        # not only when schema.py happened to run first. Production does both; a caller
        # migrating a bare legacy database does not.
        for table in missing:
            _create_table(connection, table)
        for table in stale:
            _rebuild_table(connection, table)

    # After any rebuild, because a rebuilt table is created from schema.py and already
    # has every column; this only has work to do on tables that were left alone.
    _add_missing_columns(connection)

    _stamp(connection, LATEST_VERSION)
    return LATEST_VERSION


def _existing_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if _stored_ddl(connection, table) is None:
        return set()
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def _columns_are_missing(connection: sqlite3.Connection) -> bool:
    return any(
        column not in _existing_columns(connection, table)
        for table, columns in ADDED_COLUMNS.items()
        if _stored_ddl(connection, table) is not None
        for column in columns
    )


def _add_missing_columns(connection: sqlite3.Connection) -> None:
    """Add nullable columns in place.

    SQLite refuses to alter a CHECK constraint but is perfectly happy to append a
    nullable column, so this is an ALTER rather than the rebuild `_rebuild_table` does.
    Driven by PRAGMA table_info — the columns that are actually there — for the same
    reason the CHECK check reads sqlite_master: it cannot be made stale by call order.
    """
    for table, columns in ADDED_COLUMNS.items():
        if _stored_ddl(connection, table) is None:
            continue
        present = _existing_columns(connection, table)
        for column, declaration in columns.items():
            if column in present:
                continue
            logger.info("Adding %s.%s", table, column)
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {declaration}")
    connection.commit()


def _create_table(connection: sqlite3.Connection, table: str) -> None:
    """Create a provenance table that does not exist yet, with its indexes."""
    _execute_each(connection, _TABLE_DDL[table], _TABLE_INDEXES[table])
    connection.commit()


def _current_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _stamp(connection: sqlite3.Connection, version: int) -> None:
    # PRAGMA does not accept a bound parameter, and this value is never caller-supplied.
    connection.execute(f"PRAGMA user_version = {int(version)}")
    connection.commit()


def _stored_ddl(connection: sqlite3.Connection, table: str) -> str | None:
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone()
    return None if row is None or row[0] is None else str(row[0])


def _provenance_is_stale(connection: sqlite3.Connection, table: str) -> bool:
    """True when ``table``'s stored provenance CHECK is missing a current value.

    Reading the DDL SQLite kept is the only signal that cannot be made stale by the order in
    which schema creation and migration run.
    """
    ddl = _stored_ddl(connection, table)
    if ddl is None:
        return False  # not created yet; schema.py will create it at the current shape
    return any(value not in ddl for value in PROVENANCE_VALUES)


def _rebuild_table(connection: sqlite3.Connection, table: str) -> None:
    """Recreate one table at the current shape, carrying every row across.

    SQLite cannot alter a CHECK constraint, so the table is rebuilt: create the new shape,
    copy, drop, rename, recreate indexes. Foreign keys must be off across the drop or the
    child rows are cascaded away with the table being replaced — and that PRAGMA is a no-op
    inside a transaction, so it is toggled outside one.
    """
    # Intersected with what the OLD table actually has: a rebuild may run on a database
    # that predates a later column addition, and copying a column the source lacks fails
    # with "no such column" — during a migration, which is the worst place to fail.
    present = _existing_columns(connection, table)
    columns = ", ".join(
        name
        for name in (part.strip() for part in _CARRIED_COLUMNS[table].split(","))
        if name in present
    )
    scratch = f"{table}_migrated"

    had_foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")

    try:
        connection.execute("BEGIN")
        connection.execute(
            _TABLE_DDL[table].replace(f"IF NOT EXISTS {table}", scratch)
        )
        connection.execute(
            f"INSERT INTO {scratch} ({columns}) SELECT {columns} FROM {table}"  # noqa: S608
        )
        connection.execute(f"DROP TABLE {table}")
        connection.execute(f"ALTER TABLE {scratch} RENAME TO {table}")
        # Indexes belong to the dropped table and do not survive the rename.
        # executescript() would COMMIT the open transaction, so statements are run singly.
        _execute_each(connection, _TABLE_INDEXES[table])
        connection.commit()
    except Exception:
        connection.rollback()
        logger.exception("Rebuilding %s failed; database left at its previous shape", table)
        raise
    finally:
        if had_foreign_keys:
            connection.execute("PRAGMA foreign_keys = ON")

    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        # A rebuild that loses a REFERENCES clause leaves orphans that only surface much
        # later, as rows that refuse to cascade. Fail here instead.
        raise RuntimeError(
            f"Rebuilding {table} left {len(violations)} foreign key violation(s) behind"
        )


def _execute_each(connection: sqlite3.Connection, *scripts: str) -> None:
    """Run each statement separately, keeping the caller's transaction open."""
    for script in scripts:
        for statement in script.split(";"):
            if statement.strip():
                connection.execute(statement)

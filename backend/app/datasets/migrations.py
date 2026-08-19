"""Schema migrations.

``CREATE TABLE IF NOT EXISTS`` creates tables that are missing and does **nothing** to tables
that already exist. That was sufficient while every schema change added a table — Wave 2's
``head_instances`` migrated existing installs correctly for exactly that reason. It is not
sufficient once a change modifies an existing table, because a widened CHECK constraint then
applies only to databases created after the change.

The failure mode is the dangerous kind: every test builds a fresh database and passes, while
a real install — which is the only place an *old* table exists — raises ``IntegrityError`` at
runtime. ``test_migrations.py`` therefore starts from a frozen copy of the historical DDL.

``PRAGMA user_version`` is the version marker. The previous ``SCHEMA_VERSION`` constant in
``db.py`` was never read by anything; it recorded an intention that was not implemented.
"""

from __future__ import annotations

import logging
import sqlite3

from app.datasets.schema import (
    BOX_INDEXES,
    BOXES_TABLE,
    MASK_INDEXES,
    MASKS_TABLE,
    PROVENANCE_VALUES,
)

logger = logging.getLogger(__name__)

#: Bump this with every new step below.
LATEST_VERSION = 3

# Columns carried across the v3 boxes rebuild, in a fixed order so the INSERT..SELECT cannot
# silently transpose two same-typed columns if the schema is ever reordered.
_BOX_COLUMNS = "image_id, label, provenance, prompt, score, x, y, w, h"


def run_migrations(connection: sqlite3.Connection) -> int:
    """Bring ``connection`` up to ``LATEST_VERSION``. Returns the resulting version.

    Idempotent: a database already at the latest version is left untouched, including its
    rowids — a re-run must not churn the table.
    """
    version = _current_version(connection)

    if version >= LATEST_VERSION:
        return version

    # Each step decides for itself whether it has work to do, by inspecting the schema that
    # is actually on disk rather than trusting the version stamp. This matters because
    # ``get_connection`` applies schema.py *before* calling here: any probe based on "does
    # table X exist" is already true by the time this runs, and would skip every migration.
    if _boxes_needs_rebuild(connection):
        logger.info("Migrating dataset schema to version %d", LATEST_VERSION)
        _migrate_to_v3(connection)

    _stamp(connection, LATEST_VERSION)
    return LATEST_VERSION


def _execute_each(connection: sqlite3.Connection, *scripts: str) -> None:
    """Run each statement separately, keeping the caller's transaction open."""
    for script in scripts:
        for statement in script.split(";"):
            if statement.strip():
                connection.execute(statement)


def _current_version(connection: sqlite3.Connection) -> int:
    return int(connection.execute("PRAGMA user_version").fetchone()[0])


def _stamp(connection: sqlite3.Connection, version: int) -> None:
    # PRAGMA does not accept a bound parameter, and this value is never caller-supplied.
    connection.execute(f"PRAGMA user_version = {int(version)}")
    connection.commit()


def _boxes_needs_rebuild(connection: sqlite3.Connection) -> bool:
    """True when ``boxes`` is still carrying a narrower provenance CHECK than the current one.

    Read from ``sqlite_master`` — the DDL SQLite actually stored — rather than inferred from
    a version stamp or the presence of some other table. That is the only signal that cannot
    be made stale by the order in which schema creation and migration run.
    """
    row = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='boxes'"
    ).fetchone()
    if row is None or row[0] is None:
        return False  # no boxes table yet; schema.py will create it at the current shape

    ddl = str(row[0])
    return any(value not in ddl for value in PROVENANCE_VALUES)


def _migrate_to_v3(connection: sqlite3.Connection) -> None:
    """Widen ``boxes.provenance`` and add the ``masks`` table.

    SQLite cannot alter a CHECK constraint, so ``boxes`` is rebuilt: create the new shape,
    copy every row, drop the old table, rename. Foreign keys must be off across the drop or
    the child rows are cascaded away with the table being replaced — and that PRAGMA is a
    no-op inside a transaction, so it is toggled outside one.
    """
    had_foreign_keys = bool(connection.execute("PRAGMA foreign_keys").fetchone()[0])
    connection.commit()
    connection.execute("PRAGMA foreign_keys = OFF")

    try:
        connection.execute("BEGIN")
        connection.execute(BOXES_TABLE.replace("IF NOT EXISTS boxes", "boxes_migrated"))
        connection.execute(
            f"INSERT INTO boxes_migrated ({_BOX_COLUMNS}) SELECT {_BOX_COLUMNS} FROM boxes"
        )
        connection.execute("DROP TABLE boxes")
        connection.execute("ALTER TABLE boxes_migrated RENAME TO boxes")
        # Indexes belong to the dropped table and do not survive the rename.
        # executescript() would COMMIT the open transaction, so the statements are run
        # individually instead.
        _execute_each(connection, BOX_INDEXES, MASKS_TABLE, MASK_INDEXES)
        connection.commit()
    except Exception:
        connection.rollback()
        logger.exception("Dataset schema migration to v3 failed; database left at v2")
        raise
    finally:
        if had_foreign_keys:
            connection.execute("PRAGMA foreign_keys = ON")

    violations = connection.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        # A rebuild that loses a REFERENCES clause leaves orphans that only surface much
        # later, as rows that refuse to cascade. Fail here instead.
        raise RuntimeError(
            f"Migration to v3 left {len(violations)} foreign key violation(s) behind"
        )

"""Safe, reversible fixes to a dataset before training (doc 83).

**Nothing here deletes.** A fix either takes images out of training (`images.excluded`,
reversible with one call), or records how classes should be read (`class_map` in the
dataset's preparation state), which training applies and the data never sees. Merging two
classes *in the data* could not be undone, because nothing would remember which box was
which. As a mapping it is one line to delete.

The audit applies the same state, so it always describes the dataset as training will
see it (doc 81).
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.datasets.class_names import normalise_class_name
from app.datasets.db import transaction
from app.prep.audit import last_audit
from app.prep.state import PrepState, load_state, save_state

logger = logging.getLogger(__name__)


class NoAuditError(LookupError):
    """A fix that needs the audit's findings, on a dataset never audited."""


def set_class_map(
    dataset_id: str, mapping: dict[str, str | None], settings: Settings | None = None
) -> PrepState:
    """Replace the class map, with every name normalised as training reads it."""
    state = PrepState(
        class_map={
            normalise_class_name(source): None if target is None else normalise_class_name(target)
            for source, target in mapping.items()
            if normalise_class_name(source) != (normalise_class_name(target) if target else "")
        }
    )
    save_state(dataset_id, state, settings)
    return state


def excluded_paths(dataset_id: str, settings: Settings | None = None) -> list[str]:
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT path FROM images WHERE dataset_id = ? AND COALESCE(excluded, 0) = 1"
            " ORDER BY id",
            (dataset_id,),
        ).fetchall()
    return [str(row["path"]) for row in rows]


def set_excluded(
    dataset_id: str, paths: list[str], excluded: bool, settings: Settings | None = None
) -> tuple[int, list[str]]:
    """Mark images in or out of training. Returns how many changed, and unknown paths."""
    changed = 0
    unknown: list[str] = []
    with transaction(settings) as connection:
        for path in paths:
            cursor = connection.execute(
                "UPDATE images SET excluded = ? WHERE dataset_id = ? AND path = ?"
                " AND COALESCE(excluded, 0) != ?",
                (int(excluded), dataset_id, path, int(excluded)),
            )
            if cursor.rowcount:
                changed += cursor.rowcount
            elif not connection.execute(
                "SELECT 1 FROM images WHERE dataset_id = ? AND path = ?", (dataset_id, path)
            ).fetchone():
                unknown.append(path)
    return changed, unknown


def exclude_copies(dataset_id: str, settings: Settings | None = None) -> int:
    """Keep the first image of every copy group the last audit found; exclude the rest."""
    audit = last_audit(dataset_id, settings)
    if audit is None:
        raise NoAuditError(dataset_id)
    extra = [path for group in audit.copy_groups for path in group[1:]]
    return set_excluded(dataset_id, extra, True, settings)[0]


def exclude_unreadable(dataset_id: str, settings: Settings | None = None) -> int:
    audit = last_audit(dataset_id, settings)
    if audit is None:
        raise NoAuditError(dataset_id)
    return set_excluded(dataset_id, audit.unreadable, True, settings)[0]


__all__ = [
    "NoAuditError",
    "PrepState",
    "exclude_copies",
    "exclude_unreadable",
    "excluded_paths",
    "load_state",
    "set_class_map",
    "set_excluded",
]

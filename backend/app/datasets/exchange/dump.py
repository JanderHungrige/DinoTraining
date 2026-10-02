"""Read everything a dataset holds into one JSON-ready dict (doc 142).

Rows are read with `SELECT *`, so a column added later travels without a change here.
Row ids stay in the dump only as references between rows; the restore gives new ones.
`TABLES` is the one list of what belongs to a dataset and how its rows point at each
other, read by the restore too.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from app import __version__
from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.exchange.layout import FORMAT, FORMAT_VERSION, pictures_root, relative
from app.datasets.store import dataset_dir


@dataclass(frozen=True)
class Table:
    name: str
    #: How the rows of this dataset are selected.
    where: str
    #: Columns that point at another table's rows: column -> table.
    refs: tuple[tuple[str, str], ...] = ()
    #: Whether the rows carry their own `id` that other rows point at.
    keyed: bool = True


_IMAGES = "SELECT id FROM images WHERE dataset_id = :id"
_MASKS = f"SELECT id FROM masks WHERE image_id IN ({_IMAGES})"
_PHRASES = "SELECT id FROM phrases WHERE dataset_id = :id"

#: In insert order: every table a row points at comes before the row.
TABLES: tuple[Table, ...] = (
    Table("images", "dataset_id = :id"),
    Table("boxes", f"image_id IN ({_IMAGES})", (("image_id", "images"),)),
    Table("masks", f"image_id IN ({_IMAGES})", (("image_id", "images"),)),
    Table("dataset_classes", "dataset_id = :id"),
    Table("phrases", "dataset_id = :id"),
    Table(
        "mask_phrases",
        f"mask_id IN ({_MASKS})",
        (("mask_id", "masks"), ("phrase_id", "phrases")),
        keyed=False,
    ),
    Table(
        "image_phrase_status",
        f"image_id IN ({_IMAGES})",
        (("image_id", "images"), ("phrase_id", "phrases")),
        keyed=False,
    ),
    Table("phrase_classes", f"phrase_id IN ({_PHRASES})", (("phrase_id", "phrases"),), keyed=False),
)

#: The dataset's own state, kept in its folder. `audit.json` is recomputed, not exported.
STATE_FILES = (
    "guideline.md",
    "split.json",
    "prep_state.json",
    "annotation_target.json",
    "second_look.json",
)
RECIPE_DIR = "recipes"
_NOT_EXPORTED = frozenset({"id", "export_target", "exported"})


def _rows(connection: sqlite3.Connection, table: Table, dataset_id: str) -> list[dict[str, Any]]:
    query = f"SELECT * FROM {table.name} WHERE {table.where} ORDER BY rowid"  # noqa: S608
    rows = connection.execute(query, {"id": dataset_id}).fetchall()
    return [{key: row[key] for key in row.keys() if key != "dataset_id"} for row in rows]


def _state_files(dataset_id: str, settings: Settings | None) -> dict[str, str]:
    folder = dataset_dir(dataset_id, settings)
    files = {
        name: (folder / name).read_text(encoding="utf-8")
        for name in STATE_FILES
        if (folder / name).is_file()
    }
    recipes = folder / RECIPE_DIR
    if recipes.is_dir():
        for recipe in sorted(recipes.glob("*.json")):
            files[f"{RECIPE_DIR}/{recipe.name}"] = recipe.read_text(encoding="utf-8")
    return files


def dump_dataset(dataset_id: str, settings: Settings | None = None) -> dict[str, Any]:
    """The whole dataset, picture paths relative to its pictures' folder."""
    with transaction(settings) as connection:
        dataset = connection.execute(
            "SELECT * FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
        if dataset is None:
            raise LookupError(f"No dataset {dataset_id}")
        tables = {table.name: _rows(connection, table, dataset_id) for table in TABLES}
    root = pictures_root([image["path"] for image in tables["images"]])
    for image in tables["images"]:
        image["path"] = relative(image["path"], root) if root else image["path"]
    return {
        "format": FORMAT,
        "version": FORMAT_VERSION,
        "app_version": __version__,
        "exported_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "pictures_root": str(root) if root else None,
        # Doc 143's bookkeeping is about this install's exports, not the dataset's content.
        "dataset": {key: dataset[key] for key in dataset.keys() if key not in _NOT_EXPORTED},
        "tables": tables,
        "files": _state_files(dataset_id, settings),
    }


def counts(dump: dict[str, Any]) -> tuple[int, int, int]:
    """Pictures, saved pictures and objects (boxes and masks), for summaries."""
    tables = dump["tables"]
    saved = sum(1 for image in tables["images"] if image.get("annotated_at"))
    return len(tables["images"]), saved, len(tables["boxes"]) + len(tables["masks"])


def fingerprint(dump: dict[str, Any]) -> str:
    """The content's hash, without the export's own time and app version (doc 143)."""
    content = {
        key: value for key, value in dump.items() if key not in ("exported_at", "app_version")
    }
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def to_json(dump: dict[str, Any]) -> str:
    return json.dumps(dump, indent=1, ensure_ascii=False)

"""Restore a dataset from its export (doc 142): what doc 136's import does for one.

Rows go back in one transaction with new ids, references remapped; columns this app
does not know are dropped with a warning, missing ones take their defaults. The pictures
are referenced where they are found, never copied again.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.cloud.pictures import picture_exists
from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.exchange.dump import RECIPE_DIR, STATE_FILES, TABLES, Table
from app.datasets.exchange.layout import EXPORT_DIRS, FORMAT_VERSION, FORMATS, PICTURES_DIR, resolve
from app.datasets.store import MANIFEST_NAME, DatasetStore, dataset_dir

logger = logging.getLogger(__name__)

Ids = dict[str, dict[int, int]]


@dataclass(frozen=True)
class Restored:
    dataset_id: str
    name: str
    pictures: int
    annotated_pictures: int
    objects: int
    masks: int
    classes: list[str]


def load(export_file: Path) -> dict[str, Any]:
    try:
        dump = json.loads(export_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{export_file} cannot be read: {error}") from error
    if not isinstance(dump, dict) or dump.get("format") not in FORMATS:
        raise ValueError(f"{export_file} is not a V-Rex export.")
    if int(dump.get("version", 0)) > FORMAT_VERSION:
        raise ValueError(
            f"{export_file} was written by a newer V-Rex ({dump.get('app_version')}). "
            "Update the app to restore it."
        )
    return dump


def pictures_dir(export_file: Path, dump: dict[str, Any]) -> Path | None:
    """Where the pictures are now: copied into the export, beside it, or where they were.

    The first candidate holding the first picture wins. `None` when no candidate does
    (or, for pictures stored with absolute paths, when the first one is gone).
    """
    images = dump["tables"].get("images", [])
    folder = export_file.parent
    beside = folder.parent if folder.name in EXPORT_DIRS else folder
    original = dump.get("pictures_root")
    if original is None:  # absolute paths (pictures on two Windows drives)
        return Path("/") if not images or Path(images[0]["path"]).is_file() else None
    for candidate in (folder / PICTURES_DIR, beside, Path(original)):
        if not images or picture_exists(resolve(images[0]["path"], candidate)):
            return candidate
    return None


def _columns(connection: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def _insert(connection: sqlite3.Connection, table: str, data: dict[str, Any]) -> int:
    names = list(data)
    placeholders = ", ".join("?" for _ in names)
    query = f"INSERT INTO {table} ({', '.join(names)}) VALUES ({placeholders})"  # noqa: S608
    return int(connection.execute(query, [data[name] for name in names]).lastrowid or 0)


def _row(
    table: Table, row: dict[str, Any], known: set[str], dataset_id: str, ids: Ids, root: Path | None
) -> dict[str, Any]:
    data = {key: value for key, value in row.items() if key in known and key != "id"}
    if "dataset_id" in known:
        data["dataset_id"] = dataset_id
    for column, target in table.refs:
        try:
            data[column] = ids[target][row[column]]
        except KeyError as error:
            raise ValueError(
                f"The export is damaged: {table.name} points at a missing {target} row."
            ) from error
    if table.name == "images" and root is not None and root != Path("/"):
        data["path"] = str(resolve(row["path"], root))
    return data


def _insert_tables(
    connection: sqlite3.Connection, dump: dict[str, Any], dataset_id: str, root: Path | None
) -> Ids:
    ids: Ids = {}
    for table in TABLES:
        known = _columns(connection, table.name)
        rows = dump["tables"].get(table.name, [])
        dropped = {key for row in rows for key in row} - known - {"id"}
        if dropped:
            logger.warning(
                "Restore: %s columns unknown to this app, dropped: %s", table.name, sorted(dropped)
            )
        mapping: dict[int, int] = {}
        for row in rows:
            new_id = _insert(connection, table.name, _row(table, row, known, dataset_id, ids, root))
            if table.keyed:
                mapping[row["id"]] = new_id
        ids[table.name] = mapping
    return ids


def _insert_dataset(
    connection: sqlite3.Connection,
    dump: dict[str, Any],
    dataset_id: str,
    name: str | None,
    source: str,
) -> str:
    known = _columns(connection, "datasets")
    data = {key: value for key, value in dump["dataset"].items() if key in known}
    data.update(id=dataset_id, copy_images=0, source=source)
    if name and name.strip():
        data["name"] = name.strip()
    _insert(connection, "datasets", data)
    return str(data["name"])


def _write_folder(
    folder: Path, dump: dict[str, Any], dataset_id: str, name: str, source: str
) -> None:
    (folder / "images").mkdir(parents=True, exist_ok=True)
    for relative, text in dump.get("files", {}).items():
        if relative not in STATE_FILES and not relative.startswith(f"{RECIPE_DIR}/"):
            continue  # only the files an export writes; never a path of the file's choosing
        target = folder / relative
        if relative.startswith(f"{RECIPE_DIR}/"):
            recipe = json.loads(text)
            recipe["dataset_id"] = dataset_id
            text = json.dumps(recipe, indent=2)
            target = folder / RECIPE_DIR / Path(relative).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    dataset = dump["dataset"]
    manifest = {
        "format": "dinotraining-dataset",
        "version": 1,
        "id": dataset_id,
        "name": name,
        "created_at": dataset.get("created_at"),
        "prompt": dataset.get("prompt"),
        "copy_images": False,
        "description": dataset.get("description"),
        "source": source,
        "restored": {
            "exported_at": dump.get("exported_at"),
            "app_version": dump.get("app_version"),
        },
    }
    (folder / MANIFEST_NAME).write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _classes(tables: dict[str, list[dict[str, Any]]]) -> list[str]:
    """Declared classes and every prompt an annotation carries (imports declare none)."""
    named = {row["name"] for row in tables.get("dataset_classes", [])}
    labelled = {
        row["prompt"]
        for key in ("boxes", "masks")
        for row in tables.get(key, [])
        if row.get("prompt")
    }
    return sorted(named | labelled)


def restore(
    export_file: Path, name: str | None = None, settings: Settings | None = None
) -> Restored:
    """A new dataset from an export; nothing is left behind if it fails."""
    dump = load(export_file)
    root = pictures_dir(export_file, dump)
    if root is None:
        copied = export_file.parent / PICTURES_DIR
        raise ValueError(
            f"The pictures of this export were not found: not in {copied}, "
            f"not beside the export, not at {dump.get('pictures_root')}."
        )
    dataset_id = uuid.uuid4().hex
    folder = dataset_dir(dataset_id, settings)
    source = str(export_file.parent)
    try:
        with transaction(settings) as connection:
            restored_name = _insert_dataset(connection, dump, dataset_id, name, source)
            _insert_tables(connection, dump, dataset_id, root)
        _write_folder(folder, dump, dataset_id, restored_name, source)
    except Exception:
        logger.exception("Restoring %s failed; nothing is kept", export_file)
        store = DatasetStore(settings)
        if store.exists(dataset_id):  # the rows were committed, the folder failed
            store.delete(dataset_id)
        shutil.rmtree(folder, ignore_errors=True)
        raise
    tables = dump["tables"]
    logger.info("Restored %s as %s (%d pictures)", export_file, dataset_id, len(tables["images"]))
    return Restored(
        dataset_id=dataset_id,
        name=restored_name,
        pictures=len(tables["images"]),
        annotated_pictures=sum(1 for image in tables["images"] if image.get("annotated_at")),
        objects=len(tables["boxes"]) + len(tables["masks"]),
        masks=len(tables["masks"]),
        classes=_classes(tables),
    )

"""Where a dataset's export goes, and when it last went (doc 143).

The target is "with the data" (the pictures' folder, offered only outside the app's own
data folder, which an uninstall removes) or a folder the user chose. The last export is
remembered with the content's fingerprint, so "changed since?" is a comparison that no
write path has to keep up to date.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

from app.cloud.links import Link, all_links
from app.core.config import Settings
from app.datasets.db import data_root, transaction
from app.datasets.exchange.cloud_export import export_to_bucket
from app.datasets.exchange.dump import dump_dataset, fingerprint
from app.datasets.exchange.export import ExportResult, export_dataset
from app.datasets.exchange.layout import EXPORT_DIR, pictures_root

logger = logging.getLogger(__name__)

TargetKind = Literal["data", "folder"]


class Target(BaseModel):
    kind: TargetKind
    folder: str | None = None
    include_pictures: bool = False


class Exported(BaseModel):
    at: str
    folder: str
    fingerprint: str
    #: Doc 150: the bucket's ETags of this app's last export, the condition for the next.
    e_tags: dict[str, str] = {}


class TargetView(BaseModel):
    kind: TargetKind | None
    folder: str | None
    include_pictures: bool
    #: What "with the data" means for this dataset; None where it is not offered.
    data_folder: str | None
    exported_at: str | None
    exported_folder: str | None
    #: Whether the content differs from the last export (True before the first).
    changed: bool
    #: Doc 150: "with the data" is the dataset's bucket; pictures are never copied there.
    linked: bool = False


def _read(dataset_id: str, settings: Settings | None) -> tuple[Target | None, Exported | None]:
    with transaction(settings) as connection:
        row = connection.execute(
            "SELECT export_target, exported FROM datasets WHERE id = ?", (dataset_id,)
        ).fetchone()
    if row is None:
        raise LookupError(f"No dataset {dataset_id}")
    target = Target.model_validate_json(row["export_target"]) if row["export_target"] else None
    exported = Exported.model_validate_json(row["exported"]) if row["exported"] else None
    return target, exported


def _write(dataset_id: str, column: str, value: BaseModel, settings: Settings | None) -> None:
    with transaction(settings) as connection:
        connection.execute(
            f"UPDATE datasets SET {column} = ? WHERE id = ?",  # noqa: S608 (two fixed names)
            (value.model_dump_json(), dataset_id),
        )


def data_folder(dataset_id: str, settings: Settings | None = None) -> Path | None:
    """The pictures' folder, when it lies outside the app's own data (doc 143)."""
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT path FROM images WHERE dataset_id = ?", (dataset_id,)
        ).fetchall()
    root = pictures_root([row["path"] for row in rows])
    if root is None:
        return None
    app_data = data_root(settings)
    return None if root.resolve().is_relative_to(app_data.resolve()) else root


def linked(dataset_id: str, settings: Settings | None = None) -> Link | None:
    """Doc 150: a linked dataset's "with the data" is its bucket."""
    return next((link for link in all_links(settings) if link.dataset_id == dataset_id), None)


def view(dataset_id: str, settings: Settings | None = None) -> TargetView:
    target, exported = _read(dataset_id, settings)
    link = linked(dataset_id, settings)
    offered: Path | str | None = (
        f"{link.uri}/{EXPORT_DIR}" if link else data_folder(dataset_id, settings)
    )
    current = fingerprint(dump_dataset(dataset_id, settings))
    return TargetView(
        kind=target.kind if target else None,
        folder=target.folder if target else None,
        include_pictures=(target.include_pictures if target else offered is None) and link is None,
        data_folder=str(offered) if offered else None,
        exported_at=exported.at if exported else None,
        exported_folder=exported.folder if exported else None,
        changed=exported is None or exported.fingerprint != current,
        linked=link is not None,
    )


def set_target(dataset_id: str, target: Target, settings: Settings | None = None) -> None:
    offered = linked(dataset_id, settings) or data_folder(dataset_id, settings)
    if target.kind == "data" and offered is None:
        raise ValueError(
            "This dataset's pictures live inside the app, so 'with the data' would be removed "
            "with it. Choose a folder."
        )
    if target.kind == "folder" and not (target.folder or "").strip():
        raise ValueError("Choose the folder to export to.")
    _read(dataset_id, settings)  # LookupError for an unknown dataset
    _write(dataset_id, "export_target", target, settings)


def resolve_target(dataset_id: str, target: Target, settings: Settings | None = None) -> Path:
    if target.kind == "data":
        folder = data_folder(dataset_id, settings)
        if folder is None:
            raise ValueError("'With the data' is not available for this dataset any more.")
        return folder
    return Path(target.folder or "").expanduser()


def export_to_target(dataset_id: str, settings: Settings | None = None) -> ExportResult:
    """Export to the stored target, and remember it (doc 143; doc 144 calls this too)."""
    target, exported = _read(dataset_id, settings)
    if target is None:
        raise ValueError("This dataset has no export target yet. Choose where it goes first.")
    link = linked(dataset_id, settings)
    if target.kind == "data" and link is not None:
        return _save_back(dataset_id, link, exported, settings)
    folder = resolve_target(dataset_id, target, settings)
    result = export_dataset(dataset_id, folder, target.include_pictures, settings)
    record(dataset_id, result, settings)
    return result


def _save_back(
    dataset_id: str, link: Link, exported: Exported | None, settings: Settings | None
) -> ExportResult:
    """Doc 150: into the bucket, conditional on this app's last export there."""
    last = exported.e_tags if exported and exported.folder.startswith(link.uri) else {}
    result, e_tags, text = export_to_bucket(dataset_id, link, last, settings)
    record_bucket(dataset_id, result.folder, e_tags, json.loads(text), settings)
    return result


def record_bucket(
    dataset_id: str,
    folder: str,
    e_tags: dict[str, str],
    dump: dict[str, Any],
    settings: Settings | None = None,
) -> None:
    exported = Exported(
        at=datetime.now(UTC).isoformat(timespec="seconds"),
        folder=folder,
        fingerprint=fingerprint(dump),
        e_tags=e_tags,
    )
    _write(dataset_id, "exported", exported, settings)


def record(dataset_id: str, result: ExportResult, settings: Settings | None = None) -> None:
    """Remember an export: when, where, and what the content was."""
    data = json.loads((Path(result.folder) / "dinotraining.json").read_text(encoding="utf-8"))
    exported = Exported(
        at=datetime.now(UTC).isoformat(timespec="seconds"),
        folder=result.folder,
        fingerprint=fingerprint(data),
    )
    _write(dataset_id, "exported", exported, settings)
    logger.info("Recorded the export of %s to %s", dataset_id, result.folder)


def exported_summary(
    dataset_id: str, settings: Settings | None = None
) -> tuple[str | None, str | None]:
    """When and where it was last exported, for the list (cheap: no fingerprint)."""
    _target, exported = _read(dataset_id, settings)
    return (exported.at, exported.folder) if exported else (None, None)

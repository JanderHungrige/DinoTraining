"""A linked dataset's export into its bucket (doc 150), never over someone else's newer save.

Each file is written "only if it is still the version I wrote last" (its ETag), or "only
if it does not exist" the first time. When the bucket holds a newer one, this export goes
beside it into `dinotraining/conflicts/<time>/`, and the conflict is reported: nothing is
overwritten and nothing is lost.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from app.cloud.errors import CloudConflict
from app.cloud.links import Link, storage_for
from app.core.config import Settings
from app.datasets.exchange.dump import counts, dump_dataset, to_json
from app.datasets.exchange.export import ExportResult, coco_document
from app.datasets.exchange.layout import COCO_FILE, DATA_FILE, EXPORT_DIR

logger = logging.getLogger(__name__)

KEYS = (f"{EXPORT_DIR}/{DATA_FILE}", f"{EXPORT_DIR}/{COCO_FILE}")


class ExportConflict(ValueError):
    """Someone else saved into the bucket since this app's last export (doc 150)."""


def export_to_bucket(
    dataset_id: str, link: Link, e_tags: dict[str, str], settings: Settings | None = None
) -> tuple[ExportResult, dict[str, str], str]:
    """Write the export; returns its result, the new ETags and the dump's fingerprint source."""
    dump = dump_dataset(dataset_id, settings)
    root = Path(dump["pictures_root"]) if dump["pictures_root"] else None
    texts = {KEYS[0]: to_json(dump), KEYS[1]: to_json(coco_document(dataset_id, root, settings))}
    storage = storage_for(link, settings)
    written: dict[str, str] = {}
    try:
        for key, text in texts.items():
            written[key] = storage.put_if(key, text.encode("utf-8"), e_tags.get(key)) or ""
    except CloudConflict as error:
        copy = _keep_beside(link, texts)
        logger.warning(
            "Save-back of %s met a newer export in %s (%s); kept at %s",
            dataset_id,
            link.uri,
            error,
            copy,
        )
        raise ExportConflict(
            f"Someone else saved annotations to {link.uri}/{EXPORT_DIR} since your last export. "
            f"Nothing was overwritten: yours is at {copy}."
        ) from error
    pictures, annotated, objects = counts(dump)
    result = ExportResult(
        folder=f"{link.uri}/{EXPORT_DIR}",
        pictures=pictures,
        annotated=annotated,
        objects=objects,
        pictures_copied=0,
        written_at=datetime.fromisoformat(dump["exported_at"]).isoformat(),
    )
    logger.info("Saved %s back to %s", dataset_id, result.folder)
    return result, written, to_json(dump)


def _keep_beside(link: Link, texts: dict[str, str]) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    folder = f"{EXPORT_DIR}/conflicts/{stamp}"
    storage = storage_for(link)
    for key, text in texts.items():
        storage.put(f"{folder}/{Path(key).name}", text.encode("utf-8"))
    return f"{link.uri}/{folder}"


def current_e_tags(link: Link, settings: Settings | None = None) -> dict[str, str]:
    """The bucket's export as it is now: a restore's baseline (doc 150)."""
    storage = storage_for(link, settings)
    tags: dict[str, str] = {}
    for key in KEYS:
        entry = storage.head(key)
        if entry is not None and entry.e_tag:
            tags[key] = entry.e_tag
    return tags

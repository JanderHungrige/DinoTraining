"""Dataset CRUD and the annotation write path.

The SQLite index and the on-disk `dataset.json` manifest are written in the same
transaction. SQLite is the fast lookup; the manifest is the source of truth and can
rebuild the index if the database is lost.
"""

from __future__ import annotations

import json
import logging
import shutil
import uuid
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import Settings
from app.core.paths import ensure_within
from app.datasets.db import data_root, transaction
from app.datasets.models import Box, DatasetCounts, DatasetInfo, ImageAnnotation

logger = logging.getLogger(__name__)

MANIFEST_NAME = "dataset.json"


class DatasetNotFoundError(LookupError):
    """Raised when a dataset id does not exist."""


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def datasets_root(settings: Settings | None = None) -> Path:
    return data_root(settings) / "datasets"


def dataset_dir(dataset_id: str, settings: Settings | None = None) -> Path:
    """Directory for one dataset, confined under the datasets root."""
    root = datasets_root(settings)
    return ensure_within(root, root / dataset_id)


class DatasetStore:
    """All reads and writes for datasets. Instantiated per request; holds no state."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings

    # --- creation and listing -------------------------------------------------

    def create(self, name: str, prompt: str | None, copy_images: bool) -> DatasetInfo:
        """Create a dataset. The id is generated — never caller-supplied."""
        dataset_id = uuid.uuid4().hex
        created_at = _now()

        directory = dataset_dir(dataset_id, self._settings)
        (directory / "images").mkdir(parents=True, exist_ok=True)

        with transaction(self._settings) as connection:
            connection.execute(
                "INSERT INTO datasets (id, name, created_at, prompt, copy_images)"
                " VALUES (?, ?, ?, ?, ?)",
                (dataset_id, name, created_at, prompt, int(copy_images)),
            )
            self._write_manifest(dataset_id, name, created_at, prompt, copy_images)

        logger.info("Created dataset %s (%s)", name, dataset_id)
        return DatasetInfo(
            id=dataset_id,
            name=name,
            created_at=created_at,
            prompt=prompt,
            copy_images=copy_images,
            counts=DatasetCounts(),
        )

    def list_all(self) -> list[DatasetInfo]:
        with transaction(self._settings) as connection:
            rows = connection.execute(
                "SELECT id, name, created_at, prompt, copy_images FROM datasets"
                " ORDER BY created_at DESC"
            ).fetchall()
        return [
            DatasetInfo(
                id=row["id"],
                name=row["name"],
                created_at=row["created_at"],
                prompt=row["prompt"],
                copy_images=bool(row["copy_images"]),
                counts=self.counts(row["id"]),
            )
            for row in rows
        ]

    def get(self, dataset_id: str) -> DatasetInfo:
        with transaction(self._settings) as connection:
            row = connection.execute(
                "SELECT id, name, created_at, prompt, copy_images FROM datasets WHERE id = ?",
                (dataset_id,),
            ).fetchone()
        if row is None:
            raise DatasetNotFoundError(dataset_id)
        return DatasetInfo(
            id=row["id"],
            name=row["name"],
            created_at=row["created_at"],
            prompt=row["prompt"],
            copy_images=bool(row["copy_images"]),
            counts=self.counts(dataset_id),
        )

    def exists(self, dataset_id: str) -> bool:
        with transaction(self._settings) as connection:
            return (
                connection.execute(
                    "SELECT 1 FROM datasets WHERE id = ?", (dataset_id,)
                ).fetchone()
                is not None
            )

    def delete(self, dataset_id: str) -> bool:
        """Remove the dataset rows and its directory. Returns False if unknown."""
        if not self.exists(dataset_id):
            return False

        directory = dataset_dir(dataset_id, self._settings)
        if directory == datasets_root(self._settings):
            raise ValueError("Refusing to delete the datasets root")

        with transaction(self._settings) as connection:
            # Cascades to images and boxes because foreign_keys is ON.
            connection.execute("DELETE FROM datasets WHERE id = ?", (dataset_id,))
            if directory.is_dir():
                shutil.rmtree(directory)

        logger.info("Deleted dataset %s", dataset_id)
        return True

    # --- the annotation write path --------------------------------------------

    def replace_image_boxes(self, dataset_id: str, annotation: ImageAnnotation) -> DatasetCounts:
        """Upsert one image and *replace* its boxes.

        Replace rather than append: re-reviewing an image must not leave the previous
        verdicts behind alongside the new ones.
        """
        if not self.exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        stored_path = self._store_image(dataset_id, annotation.path)

        with transaction(self._settings) as connection:
            connection.execute(
                "INSERT INTO images (dataset_id, path, width, height, annotated_at)"
                " VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(dataset_id, path) DO UPDATE SET"
                "   width = excluded.width,"
                "   height = excluded.height,"
                "   annotated_at = excluded.annotated_at",
                (dataset_id, stored_path, annotation.width, annotation.height, _now()),
            )
            row = connection.execute(
                "SELECT id FROM images WHERE dataset_id = ? AND path = ?",
                (dataset_id, stored_path),
            ).fetchone()
            image_id = int(row["id"])

            connection.execute("DELETE FROM boxes WHERE image_id = ?", (image_id,))
            connection.executemany(
                "INSERT INTO boxes"
                " (image_id, label, provenance, prompt, score, x, y, w, h)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (
                        image_id,
                        box.label,
                        box.provenance,
                        box.prompt or annotation.prompt,
                        box.score,
                        box.x,
                        box.y,
                        box.w,
                        box.h,
                    )
                    for box in annotation.boxes
                ],
            )

        return self.counts(dataset_id)

    def _store_image(self, dataset_id: str, source_path: str) -> str:
        """Copy the image into the dataset when copy_images is on; else keep the path."""
        with transaction(self._settings) as connection:
            row = connection.execute(
                "SELECT copy_images FROM datasets WHERE id = ?", (dataset_id,)
            ).fetchone()
        if row is None or not row["copy_images"]:
            return source_path

        source = Path(source_path)
        if not source.is_file():
            # Reference it anyway: a missing source is the caller's problem to report,
            # and failing the whole save would lose the labels the user just made.
            logger.warning("Cannot copy missing image %s", source_path)
            return source_path

        images_dir = dataset_dir(dataset_id, self._settings) / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        destination = ensure_within(images_dir, images_dir / source.name)
        if not destination.exists():
            shutil.copy2(source, destination)
        return str(destination)

    # --- counters --------------------------------------------------------------

    def counts(self, dataset_id: str) -> DatasetCounts:
        """Aggregate counters. SQL does the counting — never load boxes to tally them."""
        with transaction(self._settings) as connection:
            images = connection.execute(
                "SELECT COUNT(*) AS n FROM images WHERE dataset_id = ?", (dataset_id,)
            ).fetchone()["n"]
            rows = connection.execute(
                "SELECT b.label AS label, COUNT(*) AS n FROM boxes b"
                " JOIN images i ON i.id = b.image_id"
                " WHERE i.dataset_id = ?"
                " GROUP BY b.label",
                (dataset_id,),
            ).fetchall()

        by_label = {row["label"]: int(row["n"]) for row in rows}
        return DatasetCounts(
            images=int(images),
            boxes=sum(by_label.values()),
            positive=by_label.get("positive", 0),
            negative=by_label.get("negative", 0),
            unclear=by_label.get("unclear", 0),
        )

    def image_annotations(self, dataset_id: str) -> list[tuple[int, str, int, int, list[Box]]]:
        """Every image with its boxes. Used by the COCO exporter."""
        with transaction(self._settings) as connection:
            images = connection.execute(
                "SELECT id, path, width, height FROM images WHERE dataset_id = ? ORDER BY id",
                (dataset_id,),
            ).fetchall()
            result = []
            for image in images:
                boxes = connection.execute(
                    "SELECT label, provenance, prompt, score, x, y, w, h FROM boxes"
                    " WHERE image_id = ? ORDER BY id",
                    (image["id"],),
                ).fetchall()
                result.append(
                    (
                        int(image["id"]),
                        str(image["path"]),
                        int(image["width"]),
                        int(image["height"]),
                        [Box(**dict(box)) for box in boxes],
                    )
                )
        return result

    # --- manifest ---------------------------------------------------------------

    def _write_manifest(
        self,
        dataset_id: str,
        name: str,
        created_at: str,
        prompt: str | None,
        copy_images: bool,
    ) -> None:
        manifest = {
            "format": "dinotraining-dataset",
            "version": 1,
            "id": dataset_id,
            "name": name,
            "created_at": created_at,
            "prompt": prompt,
            "copy_images": copy_images,
        }
        path = dataset_dir(dataset_id, self._settings) / MANIFEST_NAME
        path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

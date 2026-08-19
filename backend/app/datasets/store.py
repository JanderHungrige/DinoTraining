"""Dataset CRUD and the annotation write path.

The SQLite index and the on-disk `dataset.json` manifest are written in the same
transaction. SQLite is the fast lookup; the manifest is the source of truth and can
rebuild the index if the database is lost.
"""

from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import uuid
from pathlib import Path

from app.core.config import Settings
from app.core.paths import ensure_within
from app.datasets.db import data_root, transaction
from app.datasets.images import now as _now
from app.datasets.images import store_image_file, upsert_image
from app.datasets.models import Box, DatasetCounts, DatasetInfo, ImageAnnotation

logger = logging.getLogger(__name__)

MANIFEST_NAME = "dataset.json"


class DatasetNotFoundError(LookupError):
    """Raised when a dataset id does not exist."""


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

        with transaction(self._settings) as connection:
            stored_path = store_image_file(
                dataset_dir(dataset_id, self._settings), connection, dataset_id, annotation.path
            )
            image_id = upsert_image(
                connection, dataset_id, stored_path, annotation.width, annotation.height
            )

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

    # --- counters --------------------------------------------------------------

    def counts(self, dataset_id: str) -> DatasetCounts:
        """Aggregate counters. SQL does the counting — never load rows to tally them.

        ``boxes`` and ``masks`` are reported separately because the trainer consumes them
        for different tasks. The per-verdict counters span both: a reviewer marking masks
        is making the same three judgements as one marking boxes, and a `positive` stuck at
        zero through a whole mask review session would be simply wrong.
        """
        with transaction(self._settings) as connection:
            images = connection.execute(
                "SELECT COUNT(*) AS n FROM images WHERE dataset_id = ?", (dataset_id,)
            ).fetchone()["n"]
            box_rows = self._labels_by_table(connection, "boxes", dataset_id)
            mask_rows = self._labels_by_table(connection, "masks", dataset_id)

        def verdict(label: str) -> int:
            return box_rows.get(label, 0) + mask_rows.get(label, 0)

        return DatasetCounts(
            images=int(images),
            boxes=sum(box_rows.values()),
            masks=sum(mask_rows.values()),
            positive=verdict("positive"),
            negative=verdict("negative"),
            unclear=verdict("unclear"),
        )

    @staticmethod
    def _labels_by_table(
        connection: sqlite3.Connection, table: str, dataset_id: str
    ) -> dict[str, int]:
        # `table` is a literal from this module, never caller-supplied — the annotation
        # values themselves stay parameterised.
        rows = connection.execute(
            f"SELECT a.label AS label, COUNT(*) AS n FROM {table} a"  # noqa: S608
            " JOIN images i ON i.id = a.image_id"
            " WHERE i.dataset_id = ?"
            " GROUP BY a.label",
            (dataset_id,),
        ).fetchall()
        return {row["label"]: int(row["n"]) for row in rows}

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

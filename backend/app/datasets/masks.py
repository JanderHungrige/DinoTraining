"""The mask write path — a sibling of ``store.py``, not an extension of it.

Masks are their own table with their own encoding concerns, and ``store.py`` was already at
the project's 300-line limit. Both paths share the image row via
``app.datasets.images.upsert_image``, so boxing and then masking the same picture updates one
image rather than creating two.
"""

from __future__ import annotations

import json
import logging

from app.core.config import Settings
from app.datasets.db import transaction
from app.datasets.images import store_image_file, upsert_image
from app.datasets.models import DatasetCounts, ImageMaskAnnotation, Mask, MaskRle
from app.datasets.rle import rle_bbox
from app.datasets.store import DatasetNotFoundError, DatasetStore, dataset_dir

logger = logging.getLogger(__name__)


class MaskStore:
    """Reads and writes for segmentation masks. Instantiated per request; holds no state."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings
        self._datasets = DatasetStore(settings)

    def replace_image_masks(
        self, dataset_id: str, annotation: ImageMaskAnnotation
    ) -> DatasetCounts:
        """Upsert one image and *replace* its masks.

        Replace rather than append, for the same reason ``replace_image_boxes`` does:
        re-reviewing an image must not leave the previous verdicts behind beside the new
        ones.
        """
        if not self._datasets.exists(dataset_id):
            raise DatasetNotFoundError(dataset_id)

        rows = [self._row(mask, annotation.prompt) for mask in annotation.masks]

        with transaction(self._settings) as connection:
            stored_path = store_image_file(
                dataset_dir(dataset_id, self._settings), connection, dataset_id, annotation.path
            )
            image_id = upsert_image(
                connection, dataset_id, stored_path, annotation.width, annotation.height
            )

            connection.execute("DELETE FROM masks WHERE image_id = ?", (image_id,))
            connection.executemany(
                "INSERT INTO masks"
                " (image_id, label, provenance, prompt, score,"
                "  rle_counts, rle_height, rle_width, x, y, w, h)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(image_id, *row) for row in rows],
            )

        return self._datasets.counts(dataset_id)

    @staticmethod
    def _row(mask: Mask, fallback_prompt: str | None) -> tuple[object, ...]:
        """Flatten one mask to its column values, deriving the bbox once on write."""
        height, width = mask.rle.size
        bbox = rle_bbox(mask.rle.counts, mask.rle.size)
        if bbox is None:
            # An all-background mask has no bounding box, and the x/y/w/h columns are NOT
            # NULL with w/h > 0. Nothing downstream can train on or render an empty mask,
            # so it is rejected rather than stored as a degenerate row.
            raise ValueError("A mask with no foreground pixels cannot be stored")

        return (
            mask.label,
            mask.provenance,
            mask.prompt or fallback_prompt,
            mask.score,
            json.dumps(mask.rle.counts),
            height,
            width,
            *bbox,
        )

    def image_masks(self, dataset_id: str) -> list[tuple[int, str, int, int, list[Mask]]]:
        """Every image with its masks, in image order. Used by the COCO exporter."""
        with transaction(self._settings) as connection:
            images = connection.execute(
                "SELECT id, path, width, height FROM images WHERE dataset_id = ? ORDER BY id",
                (dataset_id,),
            ).fetchall()
            result = []
            for image in images:
                rows = connection.execute(
                    "SELECT label, provenance, prompt, score, rle_counts, rle_height, rle_width"
                    " FROM masks WHERE image_id = ? ORDER BY id",
                    (image["id"],),
                ).fetchall()
                result.append(
                    (
                        int(image["id"]),
                        str(image["path"]),
                        int(image["width"]),
                        int(image["height"]),
                        [_mask_from_row(row) for row in rows],
                    )
                )
        return result


def _mask_from_row(row: object) -> Mask:
    mapping = dict(row)  # type: ignore[call-overload]
    return Mask(
        label=mapping["label"],
        provenance=mapping["provenance"],
        prompt=mapping["prompt"],
        score=mapping["score"],
        rle=MaskRle(
            size=(int(mapping["rle_height"]), int(mapping["rle_width"])),
            counts=json.loads(mapping["rle_counts"]),
        ),
    )

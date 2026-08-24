"""Tests for MaskStore — the replace-not-append write path, derived bboxes, counters."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.datasets.db import reset_connection, transaction
from app.datasets.masks import MaskStore
from app.datasets.models import ImageMaskAnnotation, Mask, MaskRle
from app.datasets.rle import rle_encode
from app.datasets.store import DatasetNotFoundError, DatasetStore


@pytest.fixture
def settings(tmp_path: Path) -> Iterator[Settings]:
    reset_connection()
    yield Settings(_env_file=None, data_dir=tmp_path)
    reset_connection()


@pytest.fixture
def stores(settings: Settings) -> tuple[DatasetStore, MaskStore]:
    return DatasetStore(settings), MaskStore(settings)


def rle_for(art: list[str]) -> MaskRle:
    mask = np.array([[c == "#" for c in row] for row in art], dtype=bool)
    counts, size = rle_encode(mask)
    return MaskRle(size=size, counts=counts)


def mask(art: list[str], label: str = "positive", provenance: str = "sam3", **kw: object) -> Mask:
    return Mask(label=label, provenance=provenance, rle=rle_for(art), **kw)  # type: ignore[arg-type]


#: A 4x4 frame with a 2x2 block at rows 1-2, cols 1-2.
BLOCK = ["....", ".##.", ".##.", "...."]
CORNER = ["#...", "....", "....", "...."]


def annotation(*masks: Mask, path: str = "/images/a.jpg", **kw: object) -> ImageMaskAnnotation:
    return ImageMaskAnnotation(path=path, width=4, height=4, masks=list(masks), **kw)  # type: ignore[arg-type]


class TestWrite:
    def test_it_stores_a_mask(self, stores: tuple[DatasetStore, MaskStore]) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        counts = masks.replace_image_masks(info.id, annotation(mask(BLOCK)))
        assert counts.masks == 1
        assert counts.images == 1

    def test_it_rejects_an_unknown_dataset(self, stores: tuple[DatasetStore, MaskStore]) -> None:
        _, masks = stores
        with pytest.raises(DatasetNotFoundError):
            masks.replace_image_masks("nope", annotation(mask(BLOCK)))

    def test_it_replaces_rather_than_appends(
        self, stores: tuple[DatasetStore, MaskStore]
    ) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        masks.replace_image_masks(info.id, annotation(mask(BLOCK), mask(CORNER)))
        counts = masks.replace_image_masks(info.id, annotation(mask(BLOCK)))
        assert counts.masks == 1

    def test_it_derives_and_stores_the_bounding_box(
        self, stores: tuple[DatasetStore, MaskStore], settings: Settings
    ) -> None:
        """The bbox is computed once on write so no listing has to decode an RLE."""
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        masks.replace_image_masks(info.id, annotation(mask(BLOCK)))

        with transaction(settings) as connection:
            row = connection.execute("SELECT x, y, w, h FROM masks").fetchone()
        assert (row["x"], row["y"], row["w"], row["h"]) == (1.0, 1.0, 2.0, 2.0)

    def test_it_stores_counts_as_json(
        self, stores: tuple[DatasetStore, MaskStore], settings: Settings
    ) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        expected = rle_for(BLOCK).counts
        masks.replace_image_masks(info.id, annotation(mask(BLOCK)))

        with transaction(settings) as connection:
            row = connection.execute("SELECT rle_counts FROM masks").fetchone()
        assert json.loads(row["rle_counts"]) == expected

    def test_a_mask_with_no_foreground_is_rejected(
        self, stores: tuple[DatasetStore, MaskStore]
    ) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        with pytest.raises(ValueError, match="no foreground"):
            masks.replace_image_masks(info.id, annotation(mask(["....", "....", "....", "...."])))

    def test_the_image_prompt_is_used_when_the_mask_has_none(
        self, stores: tuple[DatasetStore, MaskStore], settings: Settings
    ) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        masks.replace_image_masks(info.id, annotation(mask(BLOCK), prompt="a cat"))

        with transaction(settings) as connection:
            assert connection.execute("SELECT prompt FROM masks").fetchone()["prompt"] == "a cat"


class TestSharedImageRow:
    def test_boxing_then_masking_one_image_creates_a_single_image_row(
        self, stores: tuple[DatasetStore, MaskStore]
    ) -> None:
        """Both write paths go through upsert_image, so the picture is not duplicated."""
        from app.datasets.models import Box, ImageAnnotation

        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        datasets.replace_image_boxes(
            info.id,
            ImageAnnotation(
                path="/images/a.jpg",
                width=4,
                height=4,
                boxes=[Box(label="positive", provenance="expert-head", x=1, y=1, w=2, h=2)],
            ),
        )
        counts = masks.replace_image_masks(info.id, annotation(mask(BLOCK)))

        assert counts.images == 1
        assert counts.boxes == 1
        assert counts.masks == 1


class TestCounters:
    def test_verdicts_span_boxes_and_masks(
        self, stores: tuple[DatasetStore, MaskStore]
    ) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        counts = masks.replace_image_masks(
            info.id, annotation(mask(BLOCK, label="positive"), mask(CORNER, label="negative"))
        )
        assert (counts.positive, counts.negative, counts.unclear) == (1, 1, 0)
        assert counts.masks == 2
        assert counts.boxes == 0

    def test_deleting_the_dataset_cascades_to_masks(
        self, stores: tuple[DatasetStore, MaskStore], settings: Settings
    ) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        masks.replace_image_masks(info.id, annotation(mask(BLOCK)))
        datasets.delete(info.id)

        with transaction(settings) as connection:
            assert connection.execute("SELECT COUNT(*) AS n FROM masks").fetchone()["n"] == 0


class TestValidation:
    def test_a_mask_sized_differently_from_its_image_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="but the image is"):
            ImageMaskAnnotation(path="/a.jpg", width=8, height=8, masks=[mask(BLOCK)])

    def test_counts_that_do_not_cover_the_frame_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="sum"):
            MaskRle(size=(4, 4), counts=[3])

    def test_a_negative_run_is_rejected(self) -> None:
        with pytest.raises(ValidationError, match="negative"):
            MaskRle(size=(2, 2), counts=[5, -1])


class TestRoundTrip:
    def test_stored_masks_read_back_identically(
        self, stores: tuple[DatasetStore, MaskStore]
    ) -> None:
        datasets, masks = stores
        info = datasets.create("Cats", None, False)
        original = mask(BLOCK, label="unclear", provenance="expert-head", score=0.75)
        masks.replace_image_masks(info.id, annotation(original))

        (_, _, _, _, stored), = masks.image_masks(info.id)
        assert len(stored) == 1
        assert stored[0].label == "unclear"
        assert stored[0].provenance == "expert-head"
        assert stored[0].score == 0.75
        assert stored[0].rle.counts == original.rle.counts
        assert stored[0].rle.size == original.rle.size

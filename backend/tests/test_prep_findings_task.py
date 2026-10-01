"""Audit rules per task (doc 107): labels, outlines, SAM 3 phrases."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

import numpy as np
import pytest
from httpx import AsyncClient

from app.datasets.rle import rle_encode
from app.prep.finding_types import AuditContext
from app.prep.findings import evaluate
from app.prep.profiles import get_profile
from app.prep.task_facts import MaskFacts, PhraseFacts, collect_masks, collect_phrases
from tests.datasets_api_testkit import dataset_client, make_dataset
from tests.test_prep_findings import facts


def found(ctx: AuditContext) -> dict[str, object]:
    return {f.id: f for f in evaluate(ctx)}


class TestRules:
    def test_a_classifier_is_told_about_pictures_with_two_classes(self) -> None:
        boxes = [(0, "cat", 200), (0, "dog", 200), (1, "cat", 200)]
        result = found(AuditContext(facts(2, boxes), get_profile("head-classification-dinov2")))
        assert result["mixed-classes"].examples == ["/img/0.jpg"]  # type: ignore[attr-defined]
        # A detector trains on every object; two classes in a picture are normal there.
        assert "mixed-classes" not in found(
            AuditContext(facts(2, boxes), get_profile("rf-detr-nano"))
        )

    def test_outlines_in_pieces_and_twice(self) -> None:
        masks = MaskFacts(
            outlines=10,
            fragmented=[("/a.png", "ring", 3)],
            duplicates=[("/b.png", "ring", "blob", 0.91)],
        )
        result = found(AuditContext(facts(1, []), get_profile("sam2.1-hiera-small"), masks=masks))
        assert result["fragmented-outlines"].severity == "info"  # type: ignore[attr-defined]
        assert result["duplicate-outlines"].severity == "warn"  # type: ignore[attr-defined]

    def test_sam3_phrases_thin_bare_and_saved_before_a_class(self) -> None:
        phrases = PhraseFacts(
            phrases=[("ring", 139, 0), ("blob", 12, 2)],
            pictures=70,
            saved_before={"blob": 20, "star": 3},
        )
        result = found(AuditContext(facts(1, []), get_profile("sam3"), phrases=phrases))
        assert "blob (12)" in result["thin-phrases"].what  # type: ignore[attr-defined]
        saved = result["saved-before-class"]
        assert saved.title == "20 of 70 pictures were saved before class blob existed"  # type: ignore[attr-defined]
        assert "blob (20), star (3)" in saved.what  # type: ignore[attr-defined]
        assert "ring" in result["no-variations"].what  # type: ignore[attr-defined]

    def test_nothing_saved_before_a_class_says_nothing(self) -> None:
        phrases = PhraseFacts(phrases=[("ring", 60, 2)], pictures=5)
        result = found(AuditContext(facts(1, []), get_profile("sam3"), phrases=phrases))
        assert "saved-before-class" not in result


@pytest.fixture
async def client(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[AsyncClient, None]:
    async for c in dataset_client(tmp_path, monkeypatch):
        yield c


def _rle(mask: np.ndarray) -> dict[str, object]:
    counts, size = rle_encode(mask)
    return {"size": list(size), "counts": counts}


class TestCollection:
    async def test_pieces_and_duplicates_are_measured_from_the_pixels(
        self, client: AsyncClient
    ) -> None:
        dataset = await make_dataset(client)
        two = np.zeros((40, 40), dtype=bool)
        two[2:10, 2:10] = True
        two[20:30, 20:30] = True
        speck = np.zeros((40, 40), dtype=bool)
        speck[2:12, 2:12] = True
        speck[30, 30] = True  # one pixel: a speck, not a piece
        body = {
            "path": "/images/a.jpg",
            "width": 40,
            "height": 40,
            "masks": [
                {"label": "positive", "provenance": "sam3", "prompt": "ring", "rle": _rle(two)},
                {"label": "positive", "provenance": "sam3", "prompt": "ring", "rle": _rle(speck)},
                {"label": "positive", "provenance": "sam3", "prompt": "ring", "rle": _rle(speck)},
            ],
        }
        await client.put(f"/api/v1/datasets/{dataset['id']}/images/masks", json=body)
        masks = collect_masks(dataset["id"])
        assert masks.outlines == 3
        assert masks.fragmented == [("/images/a.jpg", "ring", 2)]
        assert [(a, b) for _, a, b, _ in masks.duplicates] == [("ring", "ring")]

    async def test_pictures_saved_with_their_classes_are_complete(
        self, client: AsyncClient
    ) -> None:
        dataset = await make_dataset(client)
        base = f"/api/v1/datasets/{dataset['id']}"
        block = np.zeros((10, 10), dtype=bool)
        block[2:5, 2:5] = True
        for name in ("a", "b"):
            body = {
                "path": f"/images/{name}.jpg",
                "width": 10,
                "height": 10,
                "masks": [
                    {
                        "label": "positive",
                        "provenance": "sam3",
                        "prompt": "ring",
                        "rle": _rle(block),
                    }
                ],
            }
            await client.put(f"{base}/images/masks", json=body)
        await client.put(
            f"{base}/images/phrase-status",
            json={"path": "/images/a.jpg", "phrase": "ring", "status": "absent"},
        )
        phrases = collect_phrases(dataset["id"])
        # Both pictures were saved with ring existing: nothing is unknown (doc 117; the
        # class-added-later case is covered with a clock in test_completeness.py).
        assert (phrases.pictures, phrases.saved_before) == (2, {})


class TestFrames:
    def test_one_object_named_two_ways_in_neighbouring_frames(self) -> None:
        from app.prep.stats import AnnotationFacts, DatasetFacts, ImageFacts

        images = [ImageFacts(i, f"/v/{i}.png", 100, 100, "ride.mp4", i) for i in range(3)]
        notes = [
            AnnotationFacts(0, "box", "positive", "signal", "signal", 10, 10, 20, 20),
            AnnotationFacts(1, "box", "positive", "light", "light", 10, 10, 21, 20),
            AnnotationFacts(2, "box", "positive", "light", "light", 10, 10, 21, 20),
        ]
        result = found(AuditContext(DatasetFacts("d", images, notes), None))
        assert result["inconsistent-frames"].examples == ["/v/1.png"]  # type: ignore[attr-defined]

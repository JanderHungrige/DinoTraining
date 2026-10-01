"""What the task-specific audit rules read (doc 107): outline shapes and phrase checks.

Collected only for targets that train on them — decoding every outline is the audit's most
expensive step, and a detector's audit has no use for it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from app.core.config import Settings
from app.datasets.completeness import completeness
from app.datasets.db import transaction
from app.datasets.phrases import PhraseStore
from app.datasets.rle import rle_decode

#: A piece smaller than this is a speck, not a part of the object.
MIN_PIECE_PX = 20
#: Two outlines overlapping this much are one object marked twice.
DUPLICATE_IOU = 0.8

#: Doc 136: a picture imported without annotations ("" = never saved) is not in training.
_INCLUDED = "COALESCE(i.excluded, 0) = 0 AND i.annotated_at != ''"


@dataclass
class MaskFacts:
    outlines: int = 0
    #: (path, class, pieces) for outlines in several pieces.
    fragmented: list[tuple[str, str, int]] = field(default_factory=list)
    #: (path, class, class, IoU) for pairs that are one object twice.
    duplicates: list[tuple[str, str, str, float]] = field(default_factory=list)


@dataclass
class PhraseFacts:
    #: (text, instances, variants) per phrase.
    phrases: list[tuple[str, int, int]] = field(default_factory=list)
    pictures: int = 0
    #: Doc 117: class → saved pictures never looked at for it (saved before it existed).
    saved_before: dict[str, int] = field(default_factory=dict)


def _pieces(mask: np.ndarray) -> int:
    labelled, count = ndimage.label(mask)
    if count <= 1:
        return int(count)
    sizes = np.bincount(labelled.ravel())[1:]
    return int((sizes >= MIN_PIECE_PX).sum())


def _overlaps(
    path: str, shapes: list[tuple[str, np.ndarray, tuple[float, float, float, float]]]
) -> list[tuple[str, str, str, float]]:
    found = []
    for i, (cls_a, mask_a, (ax, ay, aw, ah)) in enumerate(shapes):
        for cls_b, mask_b, (bx, by, bw, bh) in shapes[i + 1 :]:
            if ax > bx + bw or bx > ax + aw or ay > by + bh or by > ay + ah:
                continue
            union = np.logical_or(mask_a, mask_b).sum()
            iou = float(np.logical_and(mask_a, mask_b).sum() / union) if union else 0.0
            if iou >= DUPLICATE_IOU:
                found.append((path, cls_a, cls_b, round(iou, 3)))
    return found


def collect_masks(dataset_id: str, settings: Settings | None = None) -> MaskFacts:
    facts = MaskFacts()
    with transaction(settings) as connection:
        rows = connection.execute(
            "SELECT i.path, m.prompt, m.rle_counts, m.rle_height, m.rle_width, m.x, m.y, m.w, m.h"
            " FROM masks m JOIN images i ON i.id = m.image_id"
            f" WHERE i.dataset_id = ? AND m.label = 'positive' AND {_INCLUDED} ORDER BY i.id, m.id",
            (dataset_id,),
        ).fetchall()
    by_image: dict[str, list[tuple[str, np.ndarray, tuple[float, float, float, float]]]] = {}
    for row in rows:
        mask = rle_decode(json.loads(row["rle_counts"]), (row["rle_height"], row["rle_width"]))
        cls = str(row["prompt"] or "object")
        facts.outlines += 1
        pieces = _pieces(mask)
        if pieces > 1:
            facts.fragmented.append((str(row["path"]), cls, pieces))
        by_image.setdefault(str(row["path"]), []).append(
            (cls, mask, (row["x"], row["y"], row["w"], row["h"]))
        )
    for path, shapes in by_image.items():
        facts.duplicates.extend(_overlaps(path, shapes))
    return facts


def collect_phrases(dataset_id: str, settings: Settings | None = None) -> PhraseFacts:
    phrases = PhraseStore(settings).list_for(dataset_id)
    with transaction(settings) as connection:
        pictures = connection.execute(
            f"SELECT COUNT(*) FROM images i WHERE i.dataset_id = ? AND {_INCLUDED}", (dataset_id,)
        ).fetchone()[0]
        found = completeness(connection, dataset_id)
    return PhraseFacts(
        phrases=[(p.text, p.instances, len(p.variants)) for p in phrases],
        pictures=int(pictures),
        saved_before={
            name: int(str(info["unknown"])) for name, info in found.items() if info["unknown"]
        },
    )


__all__ = ["MaskFacts", "PhraseFacts", "collect_masks", "collect_phrases"]

"""The class vocabularies a head is built against (split from `samples.py`, doc 90).

Kept apart because the vocabulary is the one thing every consumer of a sample set must
agree on, and `samples.py` had reached the 300-line limit.
"""

from __future__ import annotations

from app.datasets.class_names import normalise_class_name
from app.datasets.models import Box, Mask


def class_name(annotation: Box | Mask) -> str:
    """A positive annotation's class is its prompt, normalised.

    Box and Mask deliberately share this: they carry the class in the same field, for the
    same reason, and a dataset with both must not end up with `signal` twice.
    """
    return normalise_class_name(annotation.prompt)


def build_class_vocabulary(
    annotations: list[tuple[int, str, int, int, list[Box]]],
) -> tuple[str, ...]:
    """Distinct classes across all positive **boxes**, sorted.

    Sorted for determinism. A class order that shifts between runs makes saved weights
    uninterpretable — index 3 would mean a different thing than it did at training time,
    and nothing about the checkpoint would reveal it.
    """
    names = {
        class_name(box)
        for _, _, _, _, boxes in annotations
        for box in boxes
        if box.label == "positive"
    }
    return tuple(sorted(names))


def build_mask_vocabulary(
    masks: list[tuple[int, str, int, int, list[Mask]]],
) -> tuple[str, ...]:
    """Distinct classes across all positive **masks**, sorted.

    Its own vocabulary rather than a union with the boxes', because the two supervise
    different heads. A dataset can hold both — thirteen box classes from a COCO import and
    one segmented class from a Grounded SAM run — and unioning them gives a segmentation
    head twelve output channels nothing can ever supervise. Harmless in that the model
    never predicts them, and confusing in the class list, the metrics and the head's name.

    The mirror is true too: a mask-only dataset has no box classes, so a detection run over
    it correctly refuses rather than training on nothing.
    """
    names = {
        class_name(mask)
        for _, _, _, _, image_masks in masks
        for mask in image_masks
        if mask.label == "positive"
    }
    return tuple(sorted(names))


__all__ = ["build_class_vocabulary", "build_mask_vocabulary", "class_name"]

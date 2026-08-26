"""Names for the classes a pretrained head predicts.

Reported as: *"the DINOv2 linear classifier (ImageNet) gives us image classes, but the
classes are not encoded — e.g. class 705, class 547."* Both of those are real answers —
`passenger car, coach, carriage` and `electric locomotive`, which on rail images is the
model getting it right and being unable to say so.

**Why the names were missing.** A head trained here records the user's own classes at save
time. A *pretrained default* is a bare `.pth` linear layer from Meta's dinov2 repo — weights
and nothing else, no `config.json`, no `id2label` — so `register_head` had no names to
store, `class_names` stayed empty, and `Prediction.class_name` fell back to its placeholder.
The fallback was correct; the gap was that nothing ever filled the list.

**Where the names come from.** Vendored JSON beside this module, fetched once and committed,
because nothing in this app may reach the network at run time. Provenance is recorded in
each file rather than in a commit message, since the question a reader will have in a year
is "can I trust this order?" and the answer has to travel with the data:

* `imagenet-1k` — from `facebook/dinov2-small-imagenet1k-1-layer`. Meta's own linear-probe
  checkpoint for the head this app loads, so the index order is the one the `.pth` was
  trained against. Not a generic ImageNet list off the internet, several of which differ.
* `ade20k` — from `nvidia/segformer-b0-finetuned-ade-512-512`, the mmseg ADE20k order, in
  which index 0 is `wall`. That is already asserted in `overlays/registry.tsx`, which dims
  class 0 only when it is *named* background — and ADE20k's is not.

**A label set is declared by the catalogue entry, never inferred from a class count.** 1000
classes does not mean ImageNet and 150 does not mean ADE20k; the next head to arrive with
150 classes would silently wear ADE20k's names, every one of them wrong and all of them
plausible.
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

_LABELS_DIR = Path(__file__).parent / "labels"

#: The label sets shipped with the app. A catalogue entry names one of these or nothing.
IMAGENET_1K = "imagenet-1k"
ADE20K = "ade20k"

LABEL_SETS: tuple[str, ...] = (IMAGENET_1K, ADE20K)


@lru_cache(maxsize=len(LABEL_SETS))
def label_names(label_set: str) -> tuple[str, ...]:
    """Every class name for a label set, in index order. Empty for an unknown one.

    Cached because the ImageNet file is 1000 entries and this is asked once per head
    registration and once per prediction payload.

    A missing or malformed file returns empty rather than raising: the names are a display
    nicety, and a head that runs correctly must not fail to *load* because its labels could
    not be read. The caller's existing `class {index}` fallback is what shows instead.
    """
    path = _LABELS_DIR / f"{label_set}.json"
    if label_set not in LABEL_SETS or not path.exists():
        logger.warning("No label set %r — class names will fall back to indices", label_set)
        return ()

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        names = payload["names"]
    except (OSError, ValueError, KeyError, TypeError):
        logger.exception("Could not read label set %r", label_set)
        return ()

    if not isinstance(names, list) or not all(isinstance(name, str) for name in names):
        logger.error("Label set %r is not a list of strings", label_set)
        return ()
    return tuple(names)


def names_for(label_set: str | None, num_classes: int) -> tuple[str, ...]:
    """Names for a head, or empty when there is no trustworthy set for it.

    **The count must match exactly.** A label set one entry short would name every class
    after it wrongly, and a reader has no way to notice — `electric locomotive` on a
    passenger car is as plausible as the truth. Refusing to guess leaves the indices
    showing, which is honest and is what happened before this module existed.
    """
    if label_set is None:
        return ()

    names = label_names(label_set)
    if not names:
        return ()
    if len(names) != num_classes:
        logger.error(
            "Label set %r has %d names but the head predicts %d classes — not applying it",
            label_set,
            len(names),
            num_classes,
        )
        return ()
    return names


__all__ = ["ADE20K", "IMAGENET_1K", "LABEL_SETS", "label_names", "names_for"]

"""Making, storing and reporting a split (doc 84)."""

from __future__ import annotations

from collections import Counter
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.datasets.db import transaction
from app.prep.audit import last_audit
from app.prep.split import BUFFER, SIDES, assign, build_groups, mark_buffers
from app.prep.state import load_state
from app.prep.stats import DatasetFacts, collect

SplitMode = Literal["auto", "keep-source"]


class SideReport(BaseModel):
    images: int
    classes: dict[str, int]


class SplitReport(BaseModel):
    mode: str
    seed: int
    groups: int
    largest_group: int
    sides: dict[str, SideReport]
    buffer: int
    warnings: list[str] = Field(default_factory=list)


class SplitRefusedError(ValueError):
    """The split asked for cannot be made, with the reason in plain language."""


NO_AUDIT_WARNING = (
    "This dataset has not been audited, so photos of the same scene could not be found and "
    "may sit on different sides. Run the audit, then split again."
)


def fractions_wanted(mode: str) -> bool:
    """Keep-source takes the import's split as it is, and an empty side there is the source's."""
    return mode == "auto"


def _report(
    facts: DatasetFacts, sides: dict[int, str], mode: str, seed: int, groups: int, largest: int
) -> SplitReport:
    per_side: dict[str, Counter[str]] = {side: Counter() for side in SIDES}
    images: Counter[str] = Counter(sides.values())
    for annotation in facts.positives():
        side = sides.get(annotation.image_id)
        if side in per_side:
            per_side[side][annotation.cls] += 1
    all_classes = sorted({a.cls for a in facts.positives()})
    warnings = []
    for side in ("val", "test"):
        missing = [name for name in all_classes if per_side[side][name] == 0]
        if images[side] and missing:
            warnings.append(
                f"{', '.join(missing[:5])} never appear{'s' if len(missing) == 1 else ''} in "
                f"{side}, so results for {'it' if len(missing) == 1 else 'them'} cannot be "
                "measured there. More examples, spread over more scenes, would fix that."
            )
        if images[side] == 0 and fractions_wanted(mode):
            warnings.append(
                f"No image ended up in {side}: the dataset has too few separate scenes or "
                "stretches of video to spare one. Add images from other scenes or videos."
            )
        if 0 < images[side] < 5:
            warnings.append(f"Only {images[side]} image(s) in {side}: too few to trust a score.")
    if groups and largest > 0.5 * len(facts.images):
        warnings.append(
            "One group holds most of the images (one long scene or video), so the sides "
            "could not be balanced. The split is still leak-free."
        )
    return SplitReport(
        mode=mode,
        seed=seed,
        groups=groups,
        largest_group=largest,
        sides={
            side: SideReport(images=images[side], classes=dict(per_side[side])) for side in SIDES
        },
        buffer=images[BUFFER],
        warnings=warnings,
    )


def make_split(
    dataset_id: str,
    val_fraction: float = 0.2,
    test_fraction: float = 0.1,
    seed: int = 42,
    mode: SplitMode = "auto",
    settings: Settings | None = None,
) -> SplitReport:
    if val_fraction < 0 or test_fraction < 0 or val_fraction + test_fraction >= 1:
        raise SplitRefusedError("The validation and test shares must be between 0 and 1 together.")
    facts = collect(dataset_id, settings, load_state(dataset_id, settings).class_map)
    if not facts.images:
        raise SplitRefusedError("There are no images to split.")
    if mode == "keep-source":
        sides = {image.id: image.split for image in facts.images if image.split in SIDES}
        if len(sides) != len(facts.images):
            raise SplitRefusedError(
                "Not every image came with a split from its source, so it cannot be kept."
            )
        return _report(facts, sides, mode, seed, 0, 0)
    audit = last_audit(dataset_id, settings)
    groups = build_groups(facts, audit.scene_groups if audit else [])
    fractions = {
        "train": 1 - val_fraction - test_fraction,
        "val": val_fraction,
        "test": test_fraction,
    }
    sides = mark_buffers(facts, assign(groups, fractions, seed))
    _store(dataset_id, sides, settings)
    largest = max(len(g.image_ids) for g in groups)
    report = _report(facts, sides, mode, seed, len(groups), largest)
    if audit is None:
        report.warnings.insert(0, NO_AUDIT_WARNING)
    return report


def _store(dataset_id: str, sides: dict[int, str], settings: Settings | None) -> None:
    with transaction(settings) as connection:
        connection.executemany(
            "UPDATE images SET split = ? WHERE id = ? AND dataset_id = ?",
            [(side, image_id, dataset_id) for image_id, side in sides.items()],
        )


def current_split(dataset_id: str, settings: Settings | None = None) -> SplitReport | None:
    """The split stored now, reported; None when no image has one."""
    facts = collect(dataset_id, settings, load_state(dataset_id, settings).class_map)
    sides = {image.id: image.split for image in facts.images if image.split}
    if not sides:
        return None
    return _report(facts, sides, "stored", 0, 0, 0)


__all__ = ["SplitRefusedError", "SplitReport", "current_split", "make_split"]

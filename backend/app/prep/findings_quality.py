"""The audit's data-quality rules: files, copies, doubt, spelling, emptiness, sequences
(doc 81). The content rules (size, classes, objects, kind) are in ``findings.py``."""

from __future__ import annotations

import re
from collections import defaultdict

from app.prep.finding_types import AuditContext, Finding


def unreadable(ctx: AuditContext) -> Finding | None:
    if not ctx.unreadable:
        return None
    return Finding(
        id="unreadable-images",
        severity="problem",
        title=f"{len(ctx.unreadable)} image(s) cannot be opened",
        what="These files are missing, moved, or damaged.",
        why="Training stops on, or silently skips, a picture it cannot read, and its "
        "annotations are lost to the model.",
        action="Restore the files, or exclude these images in the Fix step.",
        examples=ctx.unreadable[:8],
        metrics={"count": len(ctx.unreadable)},
    )


def duplicates(ctx: AuditContext) -> Finding | None:
    if not ctx.copy_groups:
        return None
    extra = sum(len(group) - 1 for group in ctx.copy_groups)
    return Finding(
        id="near-duplicates",
        severity="warn",
        title=f"{extra} copied image(s)",
        what=f"{len(ctx.copy_groups)} group(s) of images are the same picture with the same "
        "annotations (resized or re-saved copies).",
        why="Copies add no new information and make those examples count twice. If one copy "
        "is used for training and another for testing, the test only checks memory.",
        action="Keep one image per group (Fix step).",
        examples=[path for group in ctx.copy_groups[:3] for path in group[:2]],
        metrics={"groups": len(ctx.copy_groups), "extra_images": extra},
    )


def scenes(ctx: AuditContext) -> Finding | None:
    shared = sum(len(group) for group in ctx.scene_groups)
    if shared == 0:
        return None
    return Finding(
        id="shared-scenes",
        severity="info",
        title=f"{shared} images share a scene with others",
        what=f"{len(ctx.scene_groups)} group(s) of images show almost the same picture, for "
        "example the same board with a different piece on it.",
        why="These are different examples and all worth keeping. But if one of them were used "
        "for testing and its twin for training, the test would be easier than new pictures "
        "are, and the score would look too good.",
        action="Nothing to do: the split step keeps each group on one side.",
        examples=[path for group in ctx.scene_groups[:2] for path in group[:2]],
        metrics={"groups": len(ctx.scene_groups), "images": shared},
    )


def doubt(ctx: AuditContext) -> Finding | None:
    total = len(ctx.facts.annotations)
    unclear = sum(1 for a in ctx.facts.annotations if a.label == "unclear")
    if total == 0 or unclear / total <= 0.10:
        return None
    return Finding(
        id="many-unclear",
        severity="warn",
        title=f"{unclear / total:.0%} of annotations are marked unclear",
        what=f"{unclear} of {total} annotations were marked 'unclear' during review.",
        why="Unclear areas are left out of training. A high share means a lot of the data "
        "teaches nothing, or that the classes are hard to tell apart.",
        action="Review the unclear ones in the Studio. Decide yes or no where you can, and "
        "consider whether two classes should be one.",
        metrics={"unclear": unclear, "total": total},
    )


def spelling(ctx: AuditContext) -> Finding | None:
    variants: defaultdict[str, set[str]] = defaultdict(set)
    for annotation in ctx.facts.annotations:
        key = re.sub(r"[\s_\-]+", " ", annotation.cls).strip()
        key = key[:-1] if key.endswith("s") and len(key) > 3 else key
        variants[key].add(annotation.cls)
    groups = [sorted(names) for names in variants.values() if len(names) > 1]
    if not groups:
        return None
    return Finding(
        id="class-spellings",
        severity="warn",
        title="Some classes look like one class spelled two ways",
        what="; ".join(" / ".join(group) for group in groups[:5]),
        why="Training treats every spelling as its own class, so one kind of object is split "
        "in two and each half has fewer examples.",
        action="Merge the spellings in the Fix step.",
        metrics={"groups": len(groups)},
    )


def empty(ctx: AuditContext) -> Finding | None:
    annotated = {a.image_id for a in ctx.facts.positives()}
    total = len(ctx.facts.images)
    empty = total - len(annotated)
    if total == 0 or empty / total <= 0.6:
        return None
    return Finding(
        id="mostly-empty",
        severity="warn",
        title=f"{empty / total:.0%} of images have nothing annotated",
        what=f"{empty} of {total} images contain no annotated object.",
        why="Some empty images teach the model what is *not* an object, which is useful. When "
        "they are most of the dataset, the model learns that saying 'nothing' is usually right.",
        action="The Balance step can sample annotated images more often. Or exclude some of "
        "the empty ones.",
        metrics={"empty": empty, "total": total},
    )


def sequences(ctx: AuditContext) -> Finding | None:
    sequences = {image.sequence for image in ctx.facts.images if image.sequence}
    if not sequences:
        return None
    return Finding(
        id="sequences",
        severity="info",
        title=f"Frames from {len(sequences)} video(s) or folder(s)",
        what="Many images are consecutive frames, so neighbouring frames look almost identical.",
        why="If neighbouring frames were split between training and testing, the test would "
        "see almost the same picture it trained on, and the score would look far too good.",
        action="Nothing to do: the split step keeps each video's frames together.",
        metrics={"sequences": len(sequences)},
    )

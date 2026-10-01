"""Audit rules that depend on what the model trains from (doc 107).

Labels: one class per picture. Outlines: in one piece, and each object once. Phrases (SAM
3): enough of each, no pictures saved before a class existed (doc 117), variations. Each rule says
what it found, why it matters for this model, and what to do — as every rule does (doc 81).
"""

from __future__ import annotations

from collections import defaultdict

from app.prep.finding_types import AuditContext, Finding

MIN_PHRASE_INSTANCES = 50


def _examples(paths: list[str]) -> list[str]:
    return list(dict.fromkeys(paths))[:8]


def mixed_classes(ctx: AuditContext) -> Finding | None:
    if ctx.profile is None or ctx.profile.annotation_kind != "labels":
        return None
    classes: dict[int, set[str]] = defaultdict(set)
    for a in ctx.facts.positives():
        classes[a.image_id].add(a.cls)
    mixed = [ctx.facts.image(i) for i, names in classes.items() if len(names) > 1]
    paths = [image.path for image in mixed if image is not None]
    if not paths:
        return None
    return Finding(
        id="mixed-classes",
        severity="warn",
        title=f"{len(paths)} picture(s) show more than one class",
        what=f"{len(paths)} pictures carry annotations of two or more classes.",
        why="A picture classifier learns one class per picture, so it leaves these out: "
        "they are neither lesson nor test.",
        action="Mark only the main object on each, or train a detector instead, which "
        "learns every object in a picture.",
        examples=_examples(paths),
        metrics={"pictures": len(paths)},
    )


def fragmented(ctx: AuditContext) -> Finding | None:
    if ctx.masks is None or not ctx.masks.fragmented:
        return None
    items = ctx.masks.fragmented
    return Finding(
        id="fragmented-outlines",
        severity="info",
        title=f"{len(items)} outline(s) in several pieces",
        what=f"{len(items)} of {ctx.masks.outlines} outlines are split into separate pieces.",
        why="That is right for an object cut in two by something in front of it, and wrong "
        "for stray specks, which teach the model that bits of background belong to the object.",
        action="Look at the examples; remove specks with the eraser in the Annotation "
        "Studio (outline tools).",
        examples=_examples([path for path, _, _ in items]),
        metrics={"outlines": len(items)},
    )


def duplicated(ctx: AuditContext) -> Finding | None:
    if ctx.masks is None or not ctx.masks.duplicates:
        return None
    items = ctx.masks.duplicates
    return Finding(
        id="duplicate-outlines",
        severity="warn",
        title=f"{len(items)} object(s) outlined twice",
        what=f"{len(items)} pairs of outlines cover almost the same pixels (80 % or more).",
        why="One object marked twice teaches the model to find it twice, and a pair with two "
        "classes teaches it two contradictory answers.",
        action="In the Annotation Studio, reject one outline of each pair.",
        examples=_examples([path for path, *_ in items]),
        metrics={"pairs": len(items)},
    )


def thin_phrases(ctx: AuditContext) -> Finding | None:
    if ctx.phrases is None:
        return None
    thin = [(t, n) for t, n, _ in ctx.phrases.phrases if n < MIN_PHRASE_INSTANCES]
    if not thin:
        return None
    listed = ", ".join(f"{t} ({n})" for t, n in sorted(thin, key=lambda x: x[1]))
    return Finding(
        id="thin-phrases",
        severity="warn",
        title=f"{len(thin)} phrase(s) with fewer than {MIN_PHRASE_INSTANCES} outlines",
        what=f"Outlines per phrase: {listed}.",
        why="SAM 3 learns a phrase from its examples; with few it learns these pictures, "
        "not the concept.",
        action="Outline more instances of these phrases, or leave the thinnest out for now.",
        metrics={"phrases": len(thin)},
    )


def saved_before_class(ctx: AuditContext) -> Finding | None:
    """Doc 117: a class added after pictures were saved leaves those pictures unknown."""
    facts = ctx.phrases
    if facts is None or not facts.saved_before:
        return None
    worst, count = max(facts.saved_before.items(), key=lambda item: item[1])
    listed = ", ".join(f"{name} ({n})" for name, n in sorted(facts.saved_before.items()))
    return Finding(
        id="saved-before-class",
        severity="warn",
        title=f"{count} of {facts.pictures} pictures were saved before class {worst} existed",
        what=f"Pictures saved before the class existed, per class: {listed}.",
        why="A saved picture counts as complete for the classes that existed when it was "
        "saved. Pictures saved earlier were never looked at for a newer class, so SAM 3 "
        "leaves them out for it instead of learning 'none here'.",
        action="In the Annotation Studio, use 'Review for' that class: it shows only those "
        "pictures, with their saved annotations, and adds to them.",
        metrics={"pictures": count},
    )


def no_variants(ctx: AuditContext) -> Finding | None:
    if ctx.phrases is None:
        return None
    bare = [t for t, _, variants in ctx.phrases.phrases if variants == 0]
    if not bare:
        return None
    return Finding(
        id="no-variations",
        severity="info",
        title=f"{len(bare)} phrase(s) without variations",
        what=f"Only one wording for: {', '.join(bare[:10])}.",
        why="Two to four other wordings teach SAM 3 that the words can vary, so it also "
        "answers phrasings nobody typed.",
        action="Add variations under Manage phrases (comma-separated).",
        metrics={"phrases": len(bare)},
    )


FRAME_IOU = 0.7


def _iou(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    w = min(ax + aw, bx + bw) - max(ax, bx)
    h = min(ay + ah, by + bh) - max(ay, by)
    inter = max(0.0, w) * max(0.0, h)
    union = aw * ah + bw * bh - inter
    return inter / union if union else 0.0


def _frame_clashes(ctx: AuditContext) -> list[str]:
    frames = {
        (image.sequence, image.frame_index): image.id
        for image in ctx.facts.images
        if image.sequence is not None and image.frame_index is not None
    }
    boxes: dict[int, list[tuple[str, tuple[float, float, float, float]]]] = defaultdict(list)
    for a in ctx.facts.positives():
        boxes[a.image_id].append((a.cls, (a.x, a.y, a.width, a.height)))
    flagged: list[str] = []
    for (sequence, index), image_id in sorted(frames.items()):
        after = frames.get((sequence, index + 1))
        if after is None:
            continue
        clash = any(
            ca != cb and _iou(ra, rb) >= FRAME_IOU
            for ca, ra in boxes.get(image_id, [])
            for cb, rb in boxes.get(after, [])
        )
        image = ctx.facts.image(after)
        if clash and image is not None:
            flagged.append(image.path)
    return flagged


def inconsistent_frames(ctx: AuditContext) -> Finding | None:
    """Doc 109: one object named two ways in neighbouring video frames."""
    flagged = _frame_clashes(ctx)
    if not flagged:
        return None
    return Finding(
        id="inconsistent-frames",
        severity="warn",
        title=f"{len(flagged)} frame(s) name an object differently from the frame before",
        what=f"In {len(flagged)} places an object keeps its place from one frame to the next "
        "but changes its class.",
        why="The model is shown the same thing under two names, and learns neither well; "
        "every model suffers from it.",
        action="Open the frames in Inspect datasets, decide which name is right, and write it "
        "into the dataset's annotation guideline so it stays decided.",
        examples=_examples(flagged),
        metrics={"frames": len(flagged)},
    )


TASK_RULES = (
    inconsistent_frames,
    mixed_classes,
    fragmented,
    duplicated,
    thin_phrases,
    saved_before_class,
    no_variants,
)

__all__ = ["TASK_RULES"]

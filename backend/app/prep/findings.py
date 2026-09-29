"""The audit's rules: facts in, plain-language findings out (doc 81).

Every finding answers three questions for someone who has never trained a model: *what* was
found, *why it matters* for training, and *what to do*. No term is used that the finding does
not explain. The thresholds are in doc 81's table; changing one here means changing it there.

Pure functions over `AuditContext`, so every rule is testable without a database or files.
"""

from __future__ import annotations

from collections import Counter
from statistics import median

from app.prep.finding_types import SEVERITY_ORDER, AuditContext, Finding
from app.prep.findings_quality import (
    doubt,
    duplicates,
    empty,
    scenes,
    sequences,
    spelling,
    unreadable,
)
from app.prep.input_plan import decide_tiling, object_sizes


def _size(ctx: AuditContext) -> Finding | None:
    count = len(ctx.facts.images)
    if count >= 100:
        return None
    return Finding(
        id="small-dataset",
        severity="problem" if count < 20 else "warn",
        title=f"Only {count} images",
        what=f"The dataset holds {count} images.",
        why="A model learns from examples. With this few it tends to memorise these exact "
        "pictures rather than learn what the objects look like, and then fails on new ones.",
        action="Add more images if you can: a few hundred varied ones is a good start. "
        "The Dataset Generator can pre-annotate new images for you to check.",
        metrics={"images": count},
    )


def _class_counts(ctx: AuditContext) -> Counter[str]:
    return Counter(a.cls for a in ctx.facts.positives())


def _support(ctx: AuditContext) -> Finding | None:
    counts = _class_counts(ctx)
    thin = {name: n for name, n in counts.items() if n < 30}
    if not thin:
        return None
    worst = min(thin.values())
    listed = ", ".join(f"{name} ({n})" for name, n in sorted(thin.items(), key=lambda x: x[1]))
    return Finding(
        id="thin-classes",
        severity="problem" if worst < 10 else "warn",
        title=f"{len(thin)} class(es) with too few examples",
        what=f"Annotated examples per class: {listed}.",
        why="Each class is learned from its own examples. Below about 30, the model sees too "
        "few variations (angles, lighting, sizes) to recognise that class reliably.",
        action="Annotate more examples of these classes, merge a class into a similar one, "
        "or leave it out of this training run (Fix step).",
        metrics={name: n for name, n in thin.items()},
    )


def _imbalance(ctx: AuditContext) -> Finding | None:
    counts = _class_counts(ctx)
    if len(counts) < 2:
        return None
    (big, most), (small, least) = counts.most_common()[0], counts.most_common()[-1]
    ratio = most / max(1, least)
    if ratio <= 10:
        return None
    return Finding(
        id="class-imbalance",
        severity="problem" if ratio > 50 else "warn",
        title=f"Classes are very unequal ({ratio:.0f}×)",
        what=f"'{big}' has {most} examples, '{small}' only {least}.",
        why="A model rewards itself for being right often. With one class this common, it can "
        "look accurate while mostly ignoring the rare ones, and the rare ones are often the "
        "ones you care about.",
        action="The Balance step can weight the rare classes up during training. Adding "
        "examples of the rare classes helps most.",
        metrics={"ratio": round(ratio, 1), "largest": most, "smallest": least},
    )


def _object_size(ctx: AuditContext) -> Finding | None:
    profile = ctx.profile
    if profile is None or profile.annotation_kind == "labels":
        return None
    # The plan's arithmetic (doc 85), so the grid suggested here is the grid planned there.
    sized = object_sizes(ctx.facts, profile)
    if not sized:
        return None
    sizes = [size for size, _ in sized]
    p50, p10 = median(sizes), sizes[len(sizes) // 10]
    limit = profile.min_visible_px
    if p10 >= limit:
        return None
    tiling = decide_tiling(ctx.facts, profile, None)
    action = (
        f"{tiling.reason} The Model step sets tiling up and shows you what the model sees."
        if tiling.recommended
        else tiling.reason
    )
    examples: list[str] = []
    for _, annotation in sized:
        image = ctx.facts.image(annotation.image_id)
        if image is not None and image.path not in examples:
            examples.append(image.path)
        if len(examples) == 6:
            break
    return Finding(
        id="objects-too-small",
        severity="problem" if p50 < limit else "warn",
        title="Objects are too small for this model to see",
        what=f"After resizing to {profile.label}'s {profile.input_size} px input, the typical "
        f"object is {p50:.1f} px across and the smallest tenth are under {p10:.1f} px. "
        f"This model needs about {limit} px to find something.",
        why="The model shrinks every picture to a fixed size before looking at it. Objects "
        "that end up smaller than its finest detail become invisible, so it cannot learn "
        "them, however well they are labelled.",
        action=action,
        examples=examples,
        metrics={
            "median_px": round(p50, 1),
            "p10_px": round(p10, 1),
            "needed_px": limit,
            "suggested_columns": tiling.columns,
            "suggested_rows": tiling.rows,
        },
    )


def _kind(ctx: AuditContext) -> Finding | None:
    profile = ctx.profile
    if profile is None or profile.annotation_kind == "labels":
        return None
    kinds = {a.kind for a in ctx.facts.positives()}
    wanted = "mask" if profile.annotation_kind == "masks" else "box"
    if wanted in kinds:
        return None
    have = "outlines (masks)" if "mask" in kinds else "nothing usable"
    need = "outlines (masks)" if wanted == "mask" else "boxes"
    return Finding(
        id="wrong-annotation-kind",
        severity="problem",
        title=f"{profile.label} needs {need}",
        what=f"This dataset has {have}, and this model trains from {need}.",
        why="Each model learns from one kind of annotation, and cannot learn from another.",
        action="Choose a model that fits the annotations you have, or annotate with a tool "
        "that produces the right kind (Grounded SAM makes masks, Grounding DINO makes boxes).",
    )


RULES = (
    unreadable,
    _kind,
    _size,
    _support,
    _imbalance,
    _object_size,
    duplicates,
    scenes,
    spelling,
    doubt,
    empty,
    sequences,
)


def evaluate(ctx: AuditContext) -> list[Finding]:
    """All findings, most severe first."""
    found = [finding for rule in RULES if (finding := rule(ctx)) is not None]
    return sorted(found, key=lambda f: SEVERITY_ORDER.get(f.severity, 9))


__all__ = ["AuditContext", "Finding", "evaluate"]

"""What the intake check tells the user, in plain language (doc 82)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.prep.finding_types import Finding

if TYPE_CHECKING:
    from app.prep.intake import IntakeReport

_READING = {
    "xyxy": "as two corners (left, top, right, bottom)",
    "xywh-normalized": "as fractions of the image size (0 to 1)",
}


def _convention(report: IntakeReport) -> Finding | None:
    evidence = [f.evidence for f in report.files]
    boxes = sum(e.boxes for e in evidence)
    if report.convention == "xywh" or boxes == 0:
        return None
    if report.convention is None:
        shares = ", ".join(
            f"{f.source}: {f.evidence.valid_as_xywh:.0%} fit as x,y,w,h and "
            f"{f.evidence.valid_as_xyxy:.0%} as corners"
            for f in report.files
        )
        return Finding(
            id="box-convention-unclear",
            severity="problem",
            title="It is unclear how the boxes are written down",
            what=f"Neither common way of reading the numbers fits all boxes ({shares}).",
            why="A box is four numbers, and there is more than one way to write them. Read "
            "the wrong way, boxes land in the wrong place or fall outside the picture, and "
            "the model learns from boxes around nothing.",
            action="Check a few boxes in the source tool and choose the reading by hand. "
            "If the export is damaged, re-export it.",
        )
    return Finding(
        id="box-convention-converted",
        severity="info",
        title="The boxes are written differently from standard COCO",
        what=f"This export writes boxes {_READING[report.convention]}, although COCO "
        "expects left, top, width, height. All the evidence agrees.",
        why="Imported as if it were standard, most boxes would fall outside their pictures "
        "and be dropped, and the import would still say it succeeded.",
        action="Nothing to do: the import converts them. The preview after import shows the "
        "boxes on their images, so you can check.",
    )


def _missing(report: IntakeReport) -> Finding | None:
    missing = [m for f in report.files for m in f.missing_images]
    if not missing:
        return None
    total = sum(f.images for f in report.files)
    return Finding(
        id="missing-images",
        severity="problem" if len(missing) > total * 0.05 else "warn",
        title=f"{len(missing)} referenced image(s) are missing",
        what="The annotation file names pictures that are not in the folder.",
        why="Their annotations cannot be used. A large share usually means the export was "
        "unpacked into the wrong place.",
        action="Check that the images sit next to the annotation file. They will be skipped "
        "otherwise.",
        examples=missing[:8],
        metrics={"missing": len(missing), "images": total},
    )


def _sizes(report: IntakeReport) -> Finding | None:
    mismatched = [m for f in report.files for m in f.size_mismatches]
    if not mismatched:
        return None
    return Finding(
        id="size-mismatch",
        severity="problem",
        title=f"{len(mismatched)} image(s) are not the size the file says",
        what="The annotation file declares a different width or height than the real picture.",
        why="Boxes are measured against the declared size. When the picture was resized "
        "after annotating, every box is misplaced by that factor.",
        action="Re-export with the original images, or with annotations made on these images.",
        examples=mismatched[:8],
        metrics={"count": len(mismatched)},
    )


def _merges(report: IntakeReport) -> Finding | None:
    if not report.proposed_class_map:
        return None
    pairs = ", ".join(f"{a} → {b}" for a, b in list(report.proposed_class_map.items())[:6])
    return Finding(
        id="class-merges",
        severity="warn",
        title="Some class names look like one class spelled differently",
        what=f"Proposed merges: {pairs}.",
        why="Each spelling becomes its own class, so one kind of object is split in two and "
        "the model learns each half from fewer examples.",
        action="Accept the merges (the default), or untick any that are really different "
        "things, like 'glass' and 'glasses'.",
    )


def _split(report: IntakeReport) -> Finding | None:
    if not report.has_source_split:
        return None
    folders = ", ".join(sorted({f.source for f in report.files}))
    return Finding(
        id="source-split",
        severity="info",
        title="The export comes already split",
        what=f"It has separate folders: {folders}.",
        why="Whoever published the data chose which pictures are for testing. Keeping that "
        "choice makes your results comparable with theirs.",
        action="Keep it (recommended), unless the folders mix frames of one video, which the "
        "audit will point out.",
    )


def intake_findings(report: IntakeReport) -> list[Finding]:
    rules = (_convention, _missing, _sizes, _merges, _split)
    order = {"problem": 0, "warn": 1, "info": 2}
    found = [finding for rule in rules if (finding := rule(report)) is not None]
    return sorted(found, key=lambda f: order.get(f.severity, 9))


__all__ = ["intake_findings"]

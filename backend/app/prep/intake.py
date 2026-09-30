"""Checking a published dataset before it is imported (doc 82).

External data is where preparation matters most: the Generator's own datasets have known
conventions by construction, and an export from elsewhere has only its claims. This reads
a COCO export without writing anything and reports what it really contains:

* **which box convention** its numbers follow, decided from evidence (how many boxes are
  valid under each reading), not assumed;
* class names that are one class spelled several ways, with a proposed merge;
* images that are referenced but missing, or whose real size disagrees with the file;
* the export's own train/valid/test split, which the import can keep (doc 84).

The result feeds `ImportOptions`, so the import applies exactly what was checked.
"""

from __future__ import annotations

import json
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic import BaseModel, Field

from app.core.paths import ensure_within
from app.datasets.bbox_conventions import Convention
from app.datasets.class_names import normalise_class_name, spelling_key
from app.datasets.coco_import import find_coco_files, split_of
from app.prep.finding_types import Finding
from app.prep.intake_findings import intake_findings

logger = logging.getLogger(__name__)

#: Images opened per file to compare real and declared sizes. Enough to catch an export
#: whose sizes are systematically wrong, without opening ten thousand files.
SIZE_SAMPLE = 200


class ConventionEvidence(BaseModel):
    boxes: int
    #: Share of boxes that are valid, inside the frame, read each way.
    valid_as_xywh: float
    valid_as_xyxy: float
    all_normalised: bool


class IntakeFile(BaseModel):
    source: str
    split: str | None
    images: int
    annotations: int
    missing_images: list[str] = Field(default_factory=list)
    size_mismatches: list[str] = Field(default_factory=list)
    evidence: ConventionEvidence


class IntakeReport(BaseModel):
    directory: str
    files: list[IntakeFile]
    #: The convention the evidence supports, or None when it is ambiguous.
    convention: Convention | None
    classes: dict[str, int]
    #: Written name -> proposed class, for names that look like one class spelled twice.
    proposed_class_map: dict[str, str]
    has_source_split: bool
    findings: list[Finding] = Field(default_factory=list)


def _evidence(boxes: list[tuple[list[float], int, int]]) -> ConventionEvidence:
    n = len(boxes)
    xywh = xyxy = normalised = 0
    for (a, b, c, d), width, height in boxes:
        if max(a, b, c, d) <= 1.0:
            normalised += 1
        if c > 0 and d > 0 and a >= 0 and b >= 0 and a + c <= width + 0.5 and b + d <= height + 0.5:
            xywh += 1
        if c > a and d > b and a >= 0 and b >= 0 and c <= width + 0.5 and d <= height + 0.5:
            xyxy += 1
    return ConventionEvidence(
        boxes=n,
        valid_as_xywh=round(xywh / n, 4) if n else 1.0,
        valid_as_xyxy=round(xyxy / n, 4) if n else 0.0,
        all_normalised=n > 0 and normalised == n,
    )


def decide(evidence: ConventionEvidence) -> Convention | None:
    """The convention the numbers support. COCO's own wins a tie, since it is the claim."""
    if evidence.all_normalised:
        return "xywh-normalized"
    if evidence.valid_as_xywh >= 0.98:
        return "xywh"
    if evidence.valid_as_xyxy >= 0.98 and evidence.valid_as_xywh < 0.9:
        return "xyxy"
    return None


def _inspect_file(path: Path) -> tuple[IntakeFile, Counter[str]]:
    payload: dict[str, Any] = json.loads(path.read_text())
    root = path.parent
    names = {int(c["id"]): str(c.get("name", "")) for c in payload.get("categories", [])}
    images = {int(i["id"]): i for i in payload.get("images", [])}
    missing: list[str] = []
    mismatched: list[str] = []
    for index, record in enumerate(images.values()):
        file_name = str(record.get("file_name", ""))
        try:
            image_path = ensure_within(root, root / file_name)
        except ValueError:
            missing.append(file_name)
            continue
        if not image_path.is_file():
            missing.append(file_name)
        elif index < SIZE_SAMPLE:
            with Image.open(image_path) as opened:
                if opened.size != (int(record.get("width", 0)), int(record.get("height", 0))):
                    mismatched.append(file_name)
    boxes: list[tuple[list[float], int, int]] = []
    classes: Counter[str] = Counter()
    for annotation in payload.get("annotations", []):
        image = images.get(int(annotation.get("image_id", -1)))
        bbox = annotation.get("bbox")
        if image is None or not isinstance(bbox, list) or len(bbox) != 4:
            continue
        boxes.append(
            ([float(v) for v in bbox], int(image.get("width", 0)), int(image.get("height", 0)))
        )
        classes[names.get(int(annotation.get("category_id", -1)), "")] += 1
    return (
        IntakeFile(
            source=root.name,
            split=split_of(root.name),
            images=len(images),
            annotations=len(payload.get("annotations", [])),
            missing_images=missing,
            size_mismatches=mismatched,
            evidence=_evidence(boxes),
        ),
        classes,
    )


def propose_merges(classes: Counter[str]) -> dict[str, str]:
    """For each group of spellings of one class, map the rarer ones to the most used."""
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for name in classes:
        if name:
            groups[spelling_key(name)].append(name)
    proposed: dict[str, str] = {}
    for spellings in groups.values():
        if len({normalise_class_name(s) for s in spellings}) < 2:
            continue
        canonical = normalise_class_name(max(spellings, key=lambda s: classes[s]))
        for spelling in spellings:
            if normalise_class_name(spelling) != canonical:
                proposed[normalise_class_name(spelling)] = canonical
    return proposed


def inspect_coco(directory: Path) -> IntakeReport:
    paths = find_coco_files(directory)
    if not paths:
        raise ValueError(f"No COCO annotation file in {directory} or its subfolders")
    files: list[IntakeFile] = []
    classes: Counter[str] = Counter()
    for path in paths:
        try:
            inspected, counted = _inspect_file(path)
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError(f"{path.parent.name}/{path.name} cannot be read: {error}") from error
        files.append(inspected)
        classes.update(counted)
    conventions = {decide(f.evidence) for f in files}
    convention = conventions.pop() if len(conventions) == 1 else None
    report = IntakeReport(
        directory=str(directory),
        files=files,
        convention=convention,
        classes={normalise_class_name(k): v for k, v in classes.most_common() if k},
        proposed_class_map=propose_merges(classes),
        has_source_split=any(f.split for f in files),
    )
    report.findings = intake_findings(report)
    return report


__all__ = ["ConventionEvidence", "IntakeFile", "IntakeReport", "decide", "inspect_coco"]

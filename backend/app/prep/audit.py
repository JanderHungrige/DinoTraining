"""Run a dataset audit and keep its last report (doc 81)."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.datasets.store import dataset_dir
from app.prep.duplicates import clusters, dhash
from app.prep.findings import AuditContext, Finding, evaluate
from app.prep.jobs import Progress
from app.prep.profiles import get_profile
from app.prep.state import load_state
from app.prep.stats import DatasetFacts, collect

logger = logging.getLogger(__name__)

AUDIT_FILE = "audit.json"


class AuditSummary(BaseModel):
    images: int
    annotations: int
    positives: int
    classes: dict[str, int]
    problems: int
    warnings: int


class DatasetAudit(BaseModel):
    dataset_id: str
    target: str | None
    created_at: str
    summary: AuditSummary
    findings: list[Finding] = Field(default_factory=list)
    #: Content hash of the facts audited, recorded by a preparation recipe (doc 88).
    facts_hash: str
    #: In full, not as examples: doc 83 excludes all but one of each copy group, and doc 84
    #: keeps each scene group on one side of the split.
    copy_groups: list[list[str]] = Field(default_factory=list)
    scene_groups: list[list[str]] = Field(default_factory=list)
    unreadable: list[str] = Field(default_factory=list)
    #: Images a fix has taken out of training; the audit describes the rest (doc 83).
    excluded: int = 0


def facts_hash(facts: DatasetFacts) -> str:
    digest = hashlib.sha256()
    for image in facts.images:
        digest.update(f"{image.id}|{image.path}|{image.width}x{image.height}\n".encode())
    for a in facts.annotations:
        digest.update(
            f"{a.image_id}|{a.kind}|{a.label}|{a.cls}|{a.x:.1f},{a.y:.1f},"
            f"{a.width:.1f},{a.height:.1f}\n".encode()
        )
    return digest.hexdigest()[:16]


def _check_files(facts: DatasetFacts, progress: Progress) -> tuple[list[str], list[list[str]]]:
    """Every stored image opened once: unreadable ones listed, the rest grouped by scene."""
    unreadable: list[str] = []
    hashes: list[tuple[str, bytes]] = []
    total = len(facts.images)
    for index, image in enumerate(facts.images):
        value = dhash(image.path) if Path(image.path).is_file() else None
        if value is None:
            unreadable.append(image.path)
        else:
            hashes.append((image.path, value))
        if index % 25 == 0 or index == total - 1:
            progress(index + 1, total)
    return unreadable, clusters(hashes)


def copy_groups(facts: DatasetFacts, scene_groups: list[list[str]]) -> list[list[str]]:
    """Within each scene, the images whose annotations also match: the real copies."""
    ids = {image.path: image.id for image in facts.images}
    copies: list[list[str]] = []
    for scene in scene_groups:
        by_signature: dict[object, list[str]] = {}
        for path in scene:
            by_signature.setdefault(facts.signature(ids[path]), []).append(path)
        copies.extend(group for group in by_signature.values() if len(group) > 1)
    return copies


def run_audit(
    dataset_id: str,
    target: str | None,
    progress: Progress,
    settings: Settings | None = None,
) -> DatasetAudit:
    profile = get_profile(target, settings) if target else None
    facts = collect(dataset_id, settings, load_state(dataset_id, settings).class_map)
    unreadable, scene_groups = _check_files(facts, progress)
    copies = copy_groups(facts, scene_groups)
    findings = evaluate(AuditContext(facts, profile, unreadable, copies, scene_groups))
    classes: dict[str, int] = {}
    for annotation in facts.positives():
        classes[annotation.cls] = classes.get(annotation.cls, 0) + 1
    audit = DatasetAudit(
        dataset_id=dataset_id,
        target=target,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        summary=AuditSummary(
            images=len(facts.images),
            annotations=len(facts.annotations),
            positives=len(facts.positives()),
            classes=dict(sorted(classes.items(), key=lambda item: -item[1])),
            problems=sum(1 for f in findings if f.severity == "problem"),
            warnings=sum(1 for f in findings if f.severity == "warn"),
        ),
        findings=findings,
        facts_hash=facts_hash(facts),
        copy_groups=copies,
        scene_groups=scene_groups,
        unreadable=unreadable,
        excluded=facts.excluded,
    )
    _save(audit, settings)
    return audit


def _save(audit: DatasetAudit, settings: Settings | None) -> None:
    directory = dataset_dir(audit.dataset_id, settings)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / AUDIT_FILE).write_text(audit.model_dump_json(indent=2), encoding="utf-8")


def last_audit(dataset_id: str, settings: Settings | None = None) -> DatasetAudit | None:
    path = dataset_dir(dataset_id, settings) / AUDIT_FILE
    if not path.is_file():
        return None
    try:
        return DatasetAudit.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except ValueError as error:
        logger.info("Ignoring an unreadable %s: %s", path, error)
        return None


__all__ = ["DatasetAudit", "last_audit", "run_audit"]

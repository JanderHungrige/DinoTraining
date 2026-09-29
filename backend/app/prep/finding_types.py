"""What a finding is, and what the rules read (doc 81)."""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from app.prep.profiles import ModelProfile
from app.prep.stats import DatasetFacts

SEVERITY_ORDER = {"problem": 0, "warn": 1, "info": 2, "ok": 3}


class Finding(BaseModel):
    id: str
    #: "problem" blocks good training, "warn" costs quality, "info" is worth knowing.
    severity: str
    title: str
    what: str
    why: str
    action: str
    examples: list[str] = Field(default_factory=list)
    metrics: dict[str, float | int | str] = Field(default_factory=dict)


@dataclass
class AuditContext:
    facts: DatasetFacts
    profile: ModelProfile | None
    unreadable: list[str] = field(default_factory=list)
    #: Images that look the same *and* carry the same annotations: real copies.
    copy_groups: list[list[str]] = field(default_factory=list)
    #: Images that look the same, whatever they carry: one scene, kept together by the split.
    scene_groups: list[list[str]] = field(default_factory=list)

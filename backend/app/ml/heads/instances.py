"""The head-instance descriptor: what a head is, and what it was trained on.

This is the cross-tab contract. Waves 3 and 4 present heads to the user through this
type and nothing else, so a head reads identically in the viewer, the comparison panel
and the generator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

HeadInstanceKind = Literal["pretrained-default", "community", "trained-here"]

#: Human labels for tasks. Kept here rather than in the UI so the backend and the
#: frontend cannot drift into describing the same head two different ways.
TASK_LABELS: dict[str, str] = {
    "classification": "Classification",
    "detection": "Object detection",
    "segmentation": "Segmentation",
    "depth": "Depth estimation",
}

KIND_LABELS: dict[str, str] = {
    "pretrained-default": "pretrained default",
    "community": "community",
    "trained-here": "trained here",
}


@dataclass(frozen=True, slots=True)
class HeadInstance:
    """One usable head: its identity, its provenance, and where its weights live."""

    id: str
    name: str
    kind: HeadInstanceKind
    head_type_id: str
    task: str
    backbone_id: str
    backbone_family: str
    embed_dim: int
    num_classes: int
    weights_path: str
    created_at: str
    class_names: tuple[str, ...] = ()
    dataset_ids: tuple[str, ...] = ()
    metrics: dict[str, float] = field(default_factory=dict)
    primary_metric: str | None = None
    primary_metric_value: float | None = None
    config: dict[str, object] = field(default_factory=dict)
    source_repo: str | None = None
    source_digest: str | None = None
    epochs_trained: int = 0
    best_epoch: int | None = None

    @property
    def summary(self) -> str:
        """One line describing what this head does and what it learned from.

        Every picker renders this rather than composing its own, which is what stops the
        same head reading differently in two tabs — and what keeps the user from ever
        choosing between two identical-looking filenames.
        """
        parts: list[str] = [TASK_LABELS.get(self.task, self.task)]

        if self.num_classes:
            noun = "class" if self.num_classes == 1 else "classes"
            parts.append(f"{self.num_classes} {noun}")

        if self.kind == "trained-here" and self.dataset_ids:
            count = len(self.dataset_ids)
            parts.append(f"trained on {count} dataset{'' if count == 1 else 's'}")
        elif self.kind != "trained-here":
            descriptor = KIND_LABELS[self.kind]
            parts.append(f"{descriptor} ({self.source_repo})" if self.source_repo else descriptor)

        if self.primary_metric and self.primary_metric_value is not None:
            parts.append(f"{self.primary_metric} {self.primary_metric_value:.3f}")

        return " · ".join(parts)

    @property
    def runnable_on(self) -> str:
        """The backbone this head requires. Waves 3/4 use it to explain a hidden head."""
        return self.backbone_id

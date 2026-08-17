"""The head-type contract that every consumer dispatches off.

A head type is a registry entry, never an ``if task == ...`` branch. Everything a
consumer might need to know — what it trains against, which part of the backbone output
it consumes, its losses' metric names, how to pick the best epoch, how to draw its
output — is declared here, so adding a head type never edits the training loop.

This module imports **no torch**. It is read by the API on every request and by the
catalogue importer before any model is loaded; a torch import would make both slow.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal

from app.ml.registry import ModelFamily

if TYPE_CHECKING:
    from app.ml.backbone import BackboneCapabilities

HeadTask = Literal["classification", "detection", "segmentation", "depth"]
TargetFormat = Literal["image-labels", "boxes", "masks", "depth-map"]
RenderHint = Literal["labels", "boxes", "masks", "depth-map"]

#: Which part of :class:`BackboneFeatures` a head consumes.
FeatureUse = Literal["cls", "patch-grid"]

#: How preprocessing must treat geometry. ``center-crop`` is the stock classification
#: transform; ``aspect-preserve`` is mandatory for dense tasks, where a centre crop
#: silently discards annotations outside it (see doc 07's known issue).
PreprocessGeometry = Literal["center-crop", "aspect-preserve"]

MetricMode = Literal["max", "min"]


@dataclass(frozen=True, slots=True)
class HeadTypeSpec:
    """One head type. Immutable — the table is not user-editable at runtime."""

    id: str
    task: HeadTask
    title: str
    description: str
    trainable: bool
    target_format: TargetFormat | None
    consumes: FeatureUse
    geometry: PreprocessGeometry
    metrics: tuple[str, ...]
    primary_metric: str | None
    primary_metric_mode: MetricMode | None
    render_hint: RenderHint
    compatible_families: frozenset[ModelFamily]

    def __post_init__(self) -> None:
        """Enforce the invariants rather than documenting them.

        Each of these fails silently at training time if it is merely assumed: a
        trainable head with no criterion makes save-best-only keep the last epoch, and
        selecting on an uncomputed metric is a no-op that looks like it worked.
        """
        if not self.compatible_families:
            raise ValueError(f"{self.id}: compatible_families must not be empty")

        if self.trainable:
            if self.target_format is None:
                raise ValueError(f"{self.id}: a trainable head needs a target_format")
            if not self.metrics:
                raise ValueError(f"{self.id}: a trainable head needs non-empty metrics")
            if self.primary_metric is None:
                raise ValueError(
                    f"{self.id}: a trainable head needs a primary_metric, "
                    "otherwise save-best-only keeps the last epoch"
                )
            if self.primary_metric_mode is None:
                raise ValueError(f"{self.id}: primary_metric_mode must be 'max' or 'min'")
            if self.primary_metric not in self.metrics:
                raise ValueError(
                    f"{self.id}: primary_metric {self.primary_metric!r} is not in metrics "
                    f"{self.metrics!r} — it would never be computed"
                )
        else:
            if self.target_format is not None:
                raise ValueError(f"{self.id}: a non-trainable head must not set target_format")
            if self.primary_metric is not None or self.primary_metric_mode is not None:
                raise ValueError(f"{self.id}: a non-trainable head must not set primary_metric")


@dataclass(frozen=True, slots=True)
class Compatibility:
    """A verdict plus, on failure, the reason to show the user."""

    compatible: bool
    reason: str | None = None


_ALL_DINO: frozenset[ModelFamily] = frozenset({"dinov2", "dinov3"})


_SPECS: tuple[HeadTypeSpec, ...] = (
    HeadTypeSpec(
        id="linear-classifier",
        task="classification",
        title="Linear classifier",
        description=(
            "Linear probe on the pooled CLS token. Trains in seconds and is the "
            "strongest baseline for a frozen backbone."
        ),
        trainable=True,
        target_format="image-labels",
        consumes="cls",
        geometry="center-crop",
        metrics=("accuracy", "macro_f1"),
        primary_metric="accuracy",
        primary_metric_mode="max",
        render_hint="labels",
        compatible_families=_ALL_DINO,
    ),
    HeadTypeSpec(
        id="dense-detector",
        task="detection",
        title="Anchor-free detector",
        description=(
            "Per-patch classification plus box regression over the patch grid, with "
            "NMS at inference. Converges far faster than a DETR-style head on the "
            "small datasets the Annotation Studio produces."
        ),
        trainable=True,
        target_format="boxes",
        consumes="patch-grid",
        geometry="aspect-preserve",
        metrics=("map", "map_50", "map_75"),
        primary_metric="map",
        primary_metric_mode="max",
        render_hint="boxes",
        compatible_families=_ALL_DINO,
    ),
    HeadTypeSpec(
        id="linear-segmenter",
        task="segmentation",
        title="Linear segmenter",
        description=(
            "Per-patch classification upsampled to a full-resolution mask. Needs a "
            "dataset with masks — the Annotation Studio produces boxes until SAM lands."
        ),
        trainable=True,
        target_format="masks",
        consumes="patch-grid",
        geometry="aspect-preserve",
        metrics=("miou", "pixel_accuracy"),
        primary_metric="miou",
        primary_metric_mode="max",
        render_hint="masks",
        compatible_families=_ALL_DINO,
    ),
    HeadTypeSpec(
        id="linear-depth",
        task="depth",
        title="Linear depth estimator",
        description=(
            "Monocular depth from patch features. Usable via its pretrained default "
            "head; this app cannot fine-tune it, because nothing here produces depth "
            "ground truth."
        ),
        # Deliberately not trainable. This is the entry that stops every consumer from
        # assuming a training loop exists for every head type.
        trainable=False,
        target_format=None,
        consumes="patch-grid",
        geometry="aspect-preserve",
        metrics=("rmse", "abs_rel"),
        primary_metric=None,
        primary_metric_mode=None,
        render_hint="depth-map",
        compatible_families=_ALL_DINO,
    ),
)

#: Read-only view: nothing mutates the table after import.
HEAD_TYPES: MappingProxyType[str, HeadTypeSpec] = MappingProxyType(
    {spec.id: spec for spec in _SPECS}
)


def all_head_types() -> tuple[HeadTypeSpec, ...]:
    """Every head type, in display order."""
    return _SPECS


def get_head_type(head_type_id: str) -> HeadTypeSpec | None:
    """Look up a head type. Returns None for anything not in the table."""
    return HEAD_TYPES.get(head_type_id)


def head_types_for_task(task: HeadTask) -> tuple[HeadTypeSpec, ...]:
    """Every head type for one task — the basis of same-task head comparison."""
    return tuple(spec for spec in _SPECS if spec.task == task)


def trainable_head_types() -> tuple[HeadTypeSpec, ...]:
    """Head types this app can actually fine-tune. The trainer offers only these."""
    return tuple(spec for spec in _SPECS if spec.trainable)


def check_compatibility(
    spec: HeadTypeSpec, capabilities: BackboneCapabilities
) -> Compatibility:
    """Can this head type be used with this backbone, and if not, why not?

    A reason is mandatory on failure: the wave requires explaining incompatibility
    rather than greying a row out, which leaves the user with no way forward.

    Note this is a *type*-level check. A specific set of pretrained weights also has to
    match ``embed_dim``, but a linear head is constructed to whatever width the backbone
    reports, so that constraint belongs to the catalogue importer, where the weight
    shapes are already fixed.
    """
    if capabilities.family not in spec.compatible_families:
        supported = ", ".join(sorted(spec.compatible_families))
        return Compatibility(
            compatible=False,
            reason=(
                f"{spec.title} supports {supported} backbones, but "
                f"{capabilities.model_id} is {capabilities.family}."
            ),
        )
    return Compatibility(compatible=True)

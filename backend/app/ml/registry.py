"""The fixed catalogue of supported models.

This is the *only* source of downloadable repositories. A request names a registry
key; it never supplies a HuggingFace repo id. Accepting a caller-supplied repo would
let anyone reachable on loopback pull arbitrary content into the cache directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelKind = Literal["detector", "backbone"]
ModelFamily = Literal["grounding-dino", "dinov2", "dinov3"]


@dataclass(frozen=True, slots=True)
class ModelSpec:
    """One downloadable model. Immutable — the catalogue is not user-editable."""

    id: str
    repo_id: str
    kind: ModelKind
    family: ModelFamily
    gated: bool
    approx_size_mb: int
    description: str


_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="grounding-dino-tiny",
        repo_id="IDEA-Research/grounding-dino-tiny",
        kind="detector",
        family="grounding-dino",
        gated=False,
        approx_size_mb=690,
        description="Open-vocabulary detector for box proposals. Fast; start here.",
    ),
    ModelSpec(
        id="grounding-dino-base",
        repo_id="IDEA-Research/grounding-dino-base",
        kind="detector",
        family="grounding-dino",
        gated=False,
        approx_size_mb=1740,
        description="Larger open-vocabulary detector. Better recall, slower.",
    ),
    ModelSpec(
        id="dinov2-small",
        repo_id="facebook/dinov2-small",
        kind="backbone",
        family="dinov2",
        gated=False,
        approx_size_mb=88,
        description="Smallest DINOv2 backbone. Good for quick head experiments.",
    ),
    ModelSpec(
        id="dinov2-base",
        repo_id="facebook/dinov2-base",
        kind="backbone",
        family="dinov2",
        gated=False,
        approx_size_mb=330,
        description="Balanced DINOv2 backbone. Sensible default for training heads.",
    ),
    ModelSpec(
        id="dinov2-large",
        repo_id="facebook/dinov2-large",
        kind="backbone",
        family="dinov2",
        gated=False,
        approx_size_mb=1200,
        description="Large DINOv2 backbone. Stronger features, more memory.",
    ),
    ModelSpec(
        id="dinov3-vitb16",
        repo_id="facebook/dinov3-vitb16-pretrain-lvd1689m",
        kind="backbone",
        family="dinov3",
        gated=True,
        approx_size_mb=350,
        description="DINOv3 ViT-B/16. Gated — accept the licence on HuggingFace first.",
    ),
    ModelSpec(
        id="dinov3-vitl16",
        repo_id="facebook/dinov3-vitl16-pretrain-lvd1689m",
        kind="backbone",
        family="dinov3",
        gated=True,
        approx_size_mb=1200,
        description="DINOv3 ViT-L/16. Gated — accept the licence on HuggingFace first.",
    ),
)

MODELS: dict[str, ModelSpec] = {spec.id: spec for spec in _SPECS}


def licence_url(spec: ModelSpec) -> str:
    """The model's own HuggingFace page — where its licence is accepted.

    Per-model, not a constant: each gated repo has its own gate, and sending a user
    to a different model's page means they accept a licence and still get a 403.
    """
    return f"https://huggingface.co/{spec.repo_id}"


def all_models() -> tuple[ModelSpec, ...]:
    """Every catalogue entry, in display order."""
    return _SPECS


def get_model(model_id: str) -> ModelSpec | None:
    """Look up a spec by id. Returns None for anything not in the catalogue."""
    return MODELS.get(model_id)

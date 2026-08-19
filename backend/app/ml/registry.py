"""The fixed catalogue of supported models.

This is the *only* source of downloadable repositories. A request names a registry
key; it never supplies a HuggingFace repo id. Accepting a caller-supplied repo would
let anyone reachable on loopback pull arbitrary content into the cache directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelKind = Literal["detector", "backbone", "segmenter"]
ModelFamily = Literal["grounding-dino", "dinov2", "dinov3", "sam2", "sam3"]


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
    #: Shown before a download is offered, never after. Not every model here is
    #: permissively licensed — SAM 3 ships under Meta's own terms.
    licence: str = "Apache-2.0"
    #: A token alone is not always enough. DINOv3 gates on accepting terms, which is
    #: instant; SAM 3 additionally requires *manual approval* of an access request, so a
    #: 403 there means "ask for access", not "bad token". Conflating the two produces the
    #: single most confusing error this app can show.
    requires_access_request: bool = False


_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="grounding-dino-tiny",
        repo_id="IDEA-Research/grounding-dino-tiny",
        kind="detector",
        family="grounding-dino",
        gated=False,
        approx_size_mb=658,
        description="Open-vocabulary detector for box proposals. Fast; start here.",
    ),
    ModelSpec(
        id="grounding-dino-base",
        repo_id="IDEA-Research/grounding-dino-base",
        kind="detector",
        family="grounding-dino",
        gated=False,
        approx_size_mb=891,
        description="Larger open-vocabulary detector. Better recall, slower.",
    ),
    ModelSpec(
        id="dinov2-small",
        repo_id="facebook/dinov2-small",
        kind="backbone",
        family="dinov2",
        gated=False,
        approx_size_mb=84,
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
        approx_size_mb=1161,
        description="Large DINOv2 backbone. Stronger features, more memory.",
    ),
    ModelSpec(
        id="dinov3-vitb16",
        repo_id="facebook/dinov3-vitb16-pretrain-lvd1689m",
        kind="backbone",
        family="dinov3",
        gated=True,
        approx_size_mb=327,
        description="DINOv3 ViT-B/16. Gated — accept the licence on HuggingFace first.",
        licence="DINOv3 License (Meta, custom)",
    ),
    ModelSpec(
        id="dinov3-vitl16",
        repo_id="facebook/dinov3-vitl16-pretrain-lvd1689m",
        kind="backbone",
        family="dinov3",
        gated=True,
        approx_size_mb=1156,
        description="DINOv3 ViT-L/16. Gated — accept the licence on HuggingFace first.",
        licence="DINOv3 License (Meta, custom)",
    ),
    ModelSpec(
        id="sam2.1-hiera-small",
        repo_id="facebook/sam2.1-hiera-small",
        kind="segmenter",
        family="sam2",
        gated=False,
        approx_size_mb=176,
        description=(
            "Segment Anything 2.1. Turns boxes into masks. Ungated and Apache-2.0 — "
            "with Grounding DINO it gives text-prompted masks and needs no account."
        ),
    ),
    ModelSpec(
        id="sam3",
        repo_id="facebook/sam3",
        kind="segmenter",
        family="sam3",
        gated=True,
        approx_size_mb=3285,
        description=(
            "Segment Anything 3. Prompts on a text concept directly and returns masks "
            "and boxes. Needs your own HuggingFace token AND an approved access request."
        ),
        licence="SAM License (Meta, custom)",
        requires_access_request=True,
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

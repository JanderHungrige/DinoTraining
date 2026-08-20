"""The fixed catalogue of supported models.

This is the *only* source of downloadable repositories. A request names a registry
key; it never supplies a HuggingFace repo id. Accepting a caller-supplied repo would
let anyone reachable on loopback pull arbitrary content into the cache directory.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ModelKind = Literal["detector", "backbone", "segmenter", "depth-estimator"]
ModelFamily = Literal[
    "grounding-dino", "dinov2", "dinov3", "sam2", "sam3", "depth-anything"
]


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
    #: True when the licence forbids commercial use. **Explicit, never inferred from the
    #: licence string.** Substring-matching "NC" would be the same defect as reading a
    #: head's capability off its `task` label: it works until a licence is worded
    #: differently, and it fails silently in the direction that matters. This is a Wave 8
    #: packaging constraint surfaced early — an installable app cannot redistribute a
    #: non-commercial model, and the user deciding to download one should be told first.
    non_commercial: bool = False


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
    # --- foundation depth (doc 36) -----------------------------------------------
    # Depth Anything **V2**, not V3. V3 has no `transformers` integration — its config is
    # a bespoke `__object__` block, and its pip package pins `numpy<2` against this
    # environment's 2.5.2. Same reasoning that took SAM 3 over SAM 3.1: a second
    # model-loading path is not worth a benefit no wave uses. See the Wave 6 doc.
    #
    # Only **Small** is Apache-2.0. Base and Large are CC BY-NC 4.0, which is precisely
    # why doc 35 had to land first — an installable app cannot redistribute them, and the
    # person downloading one is told before the download rather than after.
    ModelSpec(
        id="depth-anything-v2-small",
        repo_id="depth-anything/Depth-Anything-V2-Small-hf",
        kind="depth-estimator",
        family="depth-anything",
        gated=False,
        approx_size_mb=95,
        description=(
            "Monocular depth from a single image. Self-contained — it brings its own "
            "backbone, so it runs beside a trained depth head rather than sharing one."
        ),
    ),
    ModelSpec(
        id="depth-anything-v2-base",
        repo_id="depth-anything/Depth-Anything-V2-Base-hf",
        kind="depth-estimator",
        family="depth-anything",
        gated=False,
        approx_size_mb=371,
        description="Larger Depth Anything V2. Sharper depth, non-commercial licence.",
        licence="CC BY-NC 4.0",
        non_commercial=True,
    ),
    ModelSpec(
        id="depth-anything-v2-large",
        repo_id="depth-anything/Depth-Anything-V2-Large-hf",
        kind="depth-estimator",
        family="depth-anything",
        gated=False,
        approx_size_mb=1250,
        description="Largest Depth Anything V2. Best quality, non-commercial licence.",
        licence="CC BY-NC 4.0",
        non_commercial=True,
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

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
    "grounding-dino", "dinov2", "dinov3", "sam2", "sam3", "depth-anything", "rf-detr"
]


Redistribution = Literal["free", "non-commercial", "copyleft", "restricted"]

#: What each answer obliges, in the words the user needs before packaging. Keyed rather
#: than composed at the call site, so the Admin panel and any future installer check cannot
#: describe the same licence differently.
REDISTRIBUTION_NOTES: dict[Redistribution, str] = {
    "free": "",
    "non-commercial": (
        "Cannot be used or shipped commercially. Remove it before distributing a "
        "commercial build."
    ),
    "copyleft": (
        "Commercial use is allowed, but distributing it obliges releasing this whole "
        "app's source under the same licence. Remove it, or accept that obligation."
    ),
    "restricted": (
        "Ships under the vendor's own terms rather than a standard licence. Read them "
        "before including it in anything you distribute."
    ),
}


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
    #: What the licence obliges when this app is **redistributed** (doc 54). Separate from
    #: `non_commercial` because the two questions are genuinely different, and conflating
    #: them is the mistake worth designing against:
    #:
    #: * `non-commercial` — CC BY-NC. May not be used or shipped commercially at all.
    #: * `copyleft` — AGPL/GPL. **Commercial use is fine.** Distributing obliges releasing
    #:   *this whole app's* source under the same licence, which is a much larger decision
    #:   than "delete it before shipping" and is not a non-commercial restriction. Nothing
    #:   in the catalogue is copyleft today; the value is naming it, because both YOLO
    #:   routes Wave 7.5 evaluated are AGPL-3.0 and that is the parked Wave 8 decision.
    #: * `restricted` — custom terms that have to be read. Meta's SAM licence is not a
    #:   standard licence and this app should not pretend to summarise it.
    #: * `free` — Apache-2.0 and friends. Ship it.
    redistribution: Redistribution = "free"
    #: Part of the set a first run needs to be useful (doc 65).
    #:
    #: **Not "small" and not "good"** — it is the smallest set that makes every tab do
    #: something: a backbone for the heads, a detector, both halves of Grounded SAM, and a
    #: depth model. Anything gated is excluded by definition, because the app cannot
    #: install it without the user doing something on HuggingFace first.
    #:
    #: Declared on the model rather than listed in the admin panel, so "what a new user
    #: needs" is answered once, next to the models, and the API and the UI cannot disagree
    #: about it.
    starter: bool = False


_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        id="grounding-dino-tiny",
        starter=True,
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
        starter=True,
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
    # --- general object detection (doc 41) ------------------------------------------
    # RF-DETR: a DINOv2 backbone, a C2f projector and a shallow 2-layer deformable DETR
    # decoder. Chosen over the DINOv2+ViTDet checkpoint (detectron2 and a bare .pth, which
    # this project refuses) and over both YOLO routes (AGPL-3.0, parked for Wave 8).
    #
    # Its backbone being a DINOv2 is not incidental: "freeze the backbone, train what sits
    # on top" — the rule this whole project is built on — applies to it unchanged, which is
    # what makes doc 44's fine-tuning a continuation rather than an exception.
    ModelSpec(
        id="rf-detr-nano",
        starter=True,
        repo_id="Roboflow/rf-detr-nano",
        kind="detector",
        family="rf-detr",
        gated=False,
        approx_size_mb=116,
        description=(
            "General object detector, COCO-pretrained on 91 classes. Needs no prompt and "
            "no training — start here for boxes."
        ),
    ),
    ModelSpec(
        id="rf-detr-small",
        repo_id="Roboflow/rf-detr-small",
        kind="detector",
        family="rf-detr",
        gated=False,
        approx_size_mb=123,
        description="Larger RF-DETR. Slower, better on small and crowded objects.",
    ),
    ModelSpec(
        id="rf-detr-base",
        repo_id="Roboflow/rf-detr-base",
        kind="detector",
        family="rf-detr",
        gated=False,
        approx_size_mb=123,
        description="Largest RF-DETR offered here. Best accuracy, highest latency.",
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
        starter=True,
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
        redistribution="non-commercial",
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
        redistribution="non-commercial",
    ),
    ModelSpec(
        id="sam2.1-hiera-small",
        starter=True,
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
        redistribution="restricted",
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

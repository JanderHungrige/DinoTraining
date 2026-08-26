"""The catalogue of self-contained foundation models.

Separate from the *head* registry on purpose, and it is the wave's main design question
answered. `run_heads` (doc 18) exists to cache **one backbone forward** and fan it out to N
heads sharing a `PassKey`. Depth Anything V2 is a complete predictor — its own DINOv2
variant, its own DPT head, its own preprocessing — so it cannot share that pass with
anything. Registering it as a `HeadInstance` whose backbone is itself would put a branch in
the one module that deliberately never branches on what it is running.

It gets its own contract instead, keyed by id, exactly as Wave 4 did for `MaskAnnotator`.
Both still produce a `Prediction` carrying a `render_hint`, so the viewer and the overlay
registry need no new concepts — which is the registry working as designed rather than being
worked around.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ml.heads.registry import RenderHint


@dataclass(frozen=True, slots=True)
class FoundationSpec:
    """One foundation model as the app offers it."""

    id: str
    #: Registry key for the weights. Never a HuggingFace repo id — doc 02's rule that a
    #: caller names a catalogue entry and never a repo holds here too.
    model_id: str
    title: str
    description: str
    task: str
    render_hint: RenderHint
    #: Where the weights live, when they are *not* a catalogue download — a fine-tuned
    #: model saved under the instance store (doc 44). `None` means "resolve `model_id`
    #: through the model cache", which is every built-in entry.
    weights_dir: Path | None = None
    #: Classes this model predicts, when they are the user's rather than COCO's.
    class_names: tuple[str, ...] = ()
    #: Set when this entry is a **concept-prompted** pipeline from `annotators/registry.py`
    #: rather than a single checkpoint (doc 45). It takes a text concept, and its install
    #: state and licence come from the several models the pipeline chains together, so
    #: `model_id` alone cannot answer either question.
    annotator_id: str | None = None
    #: Set when a *single* checkpoint needs a text prompt — Grounding DINO (doc 66).
    #:
    #: Its own field because `takes_concept` used to be defined as `annotator_id is not
    #: None`, which fused two independent axes: whether a model is prompted, and whether it
    #: is a multi-model pipeline. That held while every prompted model produced masks, and
    #: broke on the first one that produces boxes — the same defect as reading a head's
    #: capability off its `task` label.
    prompted: bool = False

    @property
    def takes_concept(self) -> bool:
        """True when this model needs a text prompt to predict anything at all."""
        return self.annotator_id is not None or self.prompted


_SPECS: tuple[FoundationSpec, ...] = (
    # --- general object detection (doc 41) ---------------------------------------
    FoundationSpec(
        id="rf-detr-nano",
        model_id="rf-detr-nano",
        title="RF-DETR (nano)",
        description="General object detection, 91 COCO classes. No prompt, no training.",
        task="detection",
        render_hint="boxes",
    ),
    FoundationSpec(
        id="rf-detr-small",
        model_id="rf-detr-small",
        title="RF-DETR (small)",
        description="Larger RF-DETR. Better on small and crowded objects.",
        task="detection",
        render_hint="boxes",
    ),
    FoundationSpec(
        id="rf-detr-base",
        model_id="rf-detr-base",
        title="RF-DETR (base)",
        description="Largest RF-DETR offered here. Best accuracy, highest latency.",
        task="detection",
        render_hint="boxes",
    ),
    # --- concept-prompted detection (doc 66) --------------------------------------
    # The Studio has offered Grounding DINO since Wave 1 as a mode of its own, which left
    # it the one model the Inference Viewer and the Generator could not run. It is neither
    # a plain detector (it needs a prompt) nor a mask annotator (it returns boxes), and the
    # catalogue had no way to say that until `prompted` existed.
    FoundationSpec(
        id="grounding-dino-tiny",
        model_id="grounding-dino-tiny",
        prompted=True,
        title="Grounding DINO (tiny)",
        description="Type what to find and it finds it — boxes, no training, no masks.",
        task="detection",
        render_hint="boxes",
    ),
    FoundationSpec(
        id="grounding-dino-base",
        model_id="grounding-dino-base",
        prompted=True,
        title="Grounding DINO (base)",
        description="Larger Grounding DINO. Better recall on hard prompts, slower.",
        task="detection",
        render_hint="boxes",
    ),
    # --- concept-prompted segmentation (doc 45) -----------------------------------
    # These were reachable only from the Dataset Generator, as `MaskAnnotator`s. They are
    # foundation models by every definition this project uses — self-contained, needing no
    # trained head — so they are listed as ones, and the Inference Viewer and the Annotation
    # Studio get them without either learning a new concept.
    FoundationSpec(
        id="grounded-sam",
        model_id="grounding-dino-tiny",
        annotator_id="grounded-sam",
        title="Grounded SAM (fast)",
        description="Segments whatever you name. Type a concept; no training.",
        task="segmentation",
        render_hint="masks",
    ),
    FoundationSpec(
        id="grounded-sam-base",
        model_id="grounding-dino-base",
        annotator_id="grounded-sam-base",
        title="Grounded SAM (base)",
        description="The same, with a bigger detector. Finds more; slower.",
        task="segmentation",
        render_hint="masks",
    ),
    FoundationSpec(
        id="grounded-sam-large",
        model_id="grounding-dino-base",
        annotator_id="grounded-sam-large",
        title="Grounded SAM (large)",
        description="Same recall as base, tighter mask edges.",
        task="segmentation",
        render_hint="masks",
    ),
    FoundationSpec(
        id="sam3",
        model_id="sam3",
        annotator_id="sam3",
        title="SAM 3",
        description="Concept segmentation in one model. Gated; needs an access request.",
        task="segmentation",
        render_hint="masks",
    ),
    # --- monocular depth (doc 36) ------------------------------------------------
    FoundationSpec(
        id="depth-anything-v2-small",
        model_id="depth-anything-v2-small",
        title="Depth Anything V2 (small)",
        description="Monocular depth from one image. Brings its own backbone.",
        task="depth",
        render_hint="depth-map",
    ),
    FoundationSpec(
        id="depth-anything-v2-base",
        model_id="depth-anything-v2-base",
        title="Depth Anything V2 (base)",
        description="Sharper monocular depth. Non-commercial licence.",
        task="depth",
        render_hint="depth-map",
    ),
    FoundationSpec(
        id="depth-anything-v2-large",
        model_id="depth-anything-v2-large",
        title="Depth Anything V2 (large)",
        description="Best-quality monocular depth. Non-commercial licence.",
        task="depth",
        render_hint="depth-map",
    ),
)


def all_foundations() -> tuple[FoundationSpec, ...]:
    return _SPECS


def get_foundation(foundation_id: str) -> FoundationSpec | None:
    return next((spec for spec in _SPECS if spec.id == foundation_id), None)


__all__ = ["FoundationSpec", "all_foundations", "get_foundation"]

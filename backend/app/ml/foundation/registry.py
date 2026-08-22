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


_SPECS: tuple[FoundationSpec, ...] = (
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

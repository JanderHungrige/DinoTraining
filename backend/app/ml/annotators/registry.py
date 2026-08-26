"""The catalogue of mask annotators.

Two catalogue layers exist deliberately. `app/ml/registry.py` lists *downloadable models*;
this lists *strategies*, and a strategy may need more than one model — `grounded-sam` needs
both a detector and a segmenter. Collapsing the two would make "is this annotator ready to
run?" unanswerable, because the answer is a property of a set of models, not of one.

An ``if annotator_id == "sam3"`` anywhere outside this module is a defect, for the same
reason a ``task ===`` comparison in ``components/overlays/`` is: the difference between the
two annotators is data, and data belongs in a registry.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.ml.registry import ModelSpec, get_model, licence_url

#: The ungated default. Keep first — display order is catalogue order, and the option that
#: needs no account should be the one a new user meets first.
GROUNDED_SAM = "grounded-sam"
#: The same pipeline with bigger halves (doc 27). Separate ids because `build_annotator`
#: dispatches on an id and readiness is a property of a *set* of models, so a variant has
#: to be a row rather than a request field.
GROUNDED_SAM_BASE = "grounded-sam-base"
GROUNDED_SAM_LARGE = "grounded-sam-large"
SAM3 = "sam3"

#: How an annotator wants its text. `phrases` takes several things at once, separated by
#: full stops — Grounding DINO was trained that way; `concept` takes one.
#:
#: Data on the spec rather than an ``annotator_id == GROUNDED_SAM`` in the UI, and not a
#: style preference: that comparison silently gave every new variant SAM 3's single-concept
#: wording while the pipeline behind it happily accepted several phrases.
PromptStyle = Literal["phrases", "concept"]


@dataclass(frozen=True, slots=True)
class AnnotatorSpec:
    """One mask-annotation strategy. Immutable — the catalogue is not user-editable."""

    id: str
    name: str
    #: Every model that must be installed before this annotator can run, in pipeline order.
    model_ids: tuple[str, ...]
    licence: str
    licence_url: str
    #: True when any required model is gated behind accepting terms.
    gated: bool
    #: True when a token is not sufficient and access must also be granted. SAM 3 only.
    requires_access_request: bool
    description: str
    prompt_style: PromptStyle = "phrases"

    @property
    def models(self) -> tuple[ModelSpec, ...]:
        specs = tuple(get_model(model_id) for model_id in self.model_ids)
        if any(spec is None for spec in specs):
            missing = [i for i, s in zip(self.model_ids, specs, strict=True) if s is None]
            raise LookupError(f"Annotator {self.id} names unknown model(s): {missing}")
        return tuple(spec for spec in specs if spec is not None)

    @property
    def approx_size_mb(self) -> int:
        """Total download for this annotator — what the admin tab must show up front."""
        return sum(spec.approx_size_mb for spec in self.models)


_SPECS: tuple[AnnotatorSpec, ...] = (
    AnnotatorSpec(
        id=GROUNDED_SAM,
        name="Grounded SAM (fast — Grounding DINO tiny + SAM 2.1 small)",
        model_ids=("grounding-dino-tiny", "sam2.1-hiera-small"),
        licence="Apache-2.0",
        licence_url="https://huggingface.co/facebook/sam2.1-hiera-small",
        gated=False,
        requires_access_request=False,
        description=(
            "Type a concept; Grounding DINO finds it and SAM 2.1 turns each box into a "
            "mask. Fully open — no account, no token, no licence to accept."
        ),
    ),
    AnnotatorSpec(
        id=GROUNDED_SAM_BASE,
        name="Grounded SAM (base — Grounding DINO base + SAM 2.1 base-plus)",
        model_ids=("grounding-dino-base", "sam2.1-hiera-base-plus"),
        licence="Apache-2.0",
        licence_url="https://huggingface.co/facebook/sam2.1-hiera-base-plus",
        gated=False,
        requires_access_request=False,
        description=(
            "The same pipeline with a bigger detector. Finds more of what you asked for "
            "— which is the half worth paying for first, since SAM cannot outline "
            "something that was never found."
        ),
    ),
    AnnotatorSpec(
        id=GROUNDED_SAM_LARGE,
        name="Grounded SAM (large — Grounding DINO base + SAM 2.1 large)",
        model_ids=("grounding-dino-base", "sam2.1-hiera-large"),
        licence="Apache-2.0",
        licence_url="https://huggingface.co/facebook/sam2.1-hiera-large",
        gated=False,
        requires_access_request=False,
        description=(
            "Same recall as base, tighter mask edges. The detector is the same one — "
            "there is no larger Grounding DINO published as open weights — so this "
            "buys outline quality, not more objects."
        ),
    ),
    AnnotatorSpec(
        id=SAM3,
        name="SAM 3 (Segment Anything with Concepts)",
        model_ids=("sam3",),
        licence="SAM License (Meta, custom)",
        licence_url="https://huggingface.co/facebook/sam3",
        gated=True,
        requires_access_request=True,
        description=(
            "Prompts on a text concept directly, in one model rather than two. Usually "
            "the better masks, but it needs your own HuggingFace token and an access "
            "request that Meta approves by hand."
        ),
        prompt_style="concept",
    ),
)

ANNOTATORS: dict[str, AnnotatorSpec] = {spec.id: spec for spec in _SPECS}


def all_annotators() -> tuple[AnnotatorSpec, ...]:
    """Every annotator, in display order — ungated first."""
    return _SPECS


def get_annotator(annotator_id: str) -> AnnotatorSpec | None:
    """Look up a spec by id. Returns None for anything not in the catalogue."""
    return ANNOTATORS.get(annotator_id)


def model_licence_url(model_id: str) -> str | None:
    """Where one required model's licence is actually read."""
    spec = get_model(model_id)
    return None if spec is None else licence_url(spec)

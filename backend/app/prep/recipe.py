"""A preparation recipe: everything decided about a dataset before training, saved (doc 88).

The guided flow (doc 89) ends here, and training (doc 90) starts here. A recipe records:

* **the data as audited**: the audit's facts hash, and its open problems;
* **the fixes**: exclusions and the class map (both are inside the facts hash, and the
  class map is kept in full so training can apply it);
* **the split**: how it was made (mode, seed, shares) and a fingerprint of the stored
  assignment, so the same recipe gives the same split and a changed one is noticed;
* **the input plan**: fit, input size and tiling (doc 85);
* **imbalance and augmentation** (docs 86, 87), as the training fields that apply them.

Recipes are never edited. Saving under an existing name makes the next version, so a
trained head's provenance can name exactly the recipe it used.

**Out of date is a state, not an error.** When the data, the fixes or the split change
after a recipe is saved, `check` says what changed; training (doc 90) refuses a stale
recipe with that reason rather than training on something the recipe does not describe.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, Field

from app.core.config import Settings
from app.datasets.store import dataset_dir
from app.ml.augment import PRESETS
from app.ml.training.imbalance import STRATEGIES
from app.prep.audit import facts_hash, last_audit
from app.prep.input_plan import plan_input
from app.prep.profiles import get_profile
from app.prep.split_service import current_split, load_split_settings, split_hash
from app.prep.state import load_state
from app.prep.stats import collect

logger = logging.getLogger(__name__)

RECIPE_DIR = "recipes"


class RecipeRefusedError(ValueError):
    """A recipe cannot be saved yet; the message says what step is missing."""


class RecipeSplit(BaseModel):
    mode: str
    seed: int
    val_fraction: float
    test_fraction: float
    sides: dict[str, int]
    buffer: int
    fingerprint: str


class RecipeTiling(BaseModel):
    columns: int
    rows: int
    overlap: float


class RecipePhrase(BaseModel):
    """A phrase as it was when the recipe was saved (doc 108): provenance for SAM 3."""

    text: str
    class_name: str
    variants: list[str] = Field(default_factory=list)
    confusable: list[str] = Field(default_factory=list)
    #: Doc 115: an umbrella term's member classes; empty for an ordinary phrase.
    classes: list[str] = Field(default_factory=list)


class Recipe(BaseModel):
    id: str
    name: str
    version: int
    created_at: str
    dataset_id: str
    target: str
    facts_hash: str
    class_map: dict[str, str | None]
    excluded: int
    split: RecipeSplit
    fit: str
    input_size: int
    tiling: RecipeTiling | None
    imbalance: str
    augmentation: str
    augment_copies: int
    #: Open problems from the audit, by title: saved knowingly, and shown with the recipe.
    open_problems: list[str] = Field(default_factory=list)
    #: SAM 3's phrases when saved (doc 108). Training reads the live phrases; this records
    #: which wordings and look-alikes a recipe was made with.
    prompts: list[RecipePhrase] | None = None

    def training_fields(self) -> dict[str, object]:
        """The training request fields this recipe sets (doc 90 adds the rest)."""
        return {
            "imbalance": self.imbalance,
            "augmentation": self.augmentation,
            "augment_copies": self.augment_copies,
        }


class RecipeRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    target: str
    imbalance: str = "none"
    augmentation: str = "none"
    augment_copies: int = Field(default=2, ge=0, le=8)
    #: Tiles along the long edge; None takes the input plan's choice.
    grid: int | None = Field(default=None, ge=1, le=6)


def list_recipes(dataset_id: str, settings: Settings | None = None) -> list[Recipe]:
    directory = dataset_dir(dataset_id, settings) / RECIPE_DIR
    recipes = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            recipes.append(Recipe.model_validate(json.loads(path.read_text(encoding="utf-8"))))
        except ValueError as error:
            logger.warning("Skipping an unreadable recipe %s: %s", path, error)
    return sorted(recipes, key=lambda r: (r.created_at, r.version))


def get_recipe(dataset_id: str, recipe_id: str, settings: Settings | None = None) -> Recipe | None:
    return next((r for r in list_recipes(dataset_id, settings) if r.id == recipe_id), None)


def _validate(request: RecipeRequest) -> None:
    """Invalid input (a 422), as opposed to a missing step (`RecipeRefusedError`, a 409)."""
    if request.imbalance not in STRATEGIES:
        raise ValueError(f"Unknown imbalance strategy: {request.imbalance}")
    if request.augmentation not in PRESETS:
        raise ValueError(f"Unknown augmentation preset: {request.augmentation}")
    try:
        get_profile(request.target)
    except KeyError as error:
        raise ValueError(f"Unknown target: {request.target}") from error


def _split(dataset_id: str, settings: Settings | None) -> RecipeSplit:
    report = current_split(dataset_id, settings)
    made = load_split_settings(dataset_id, settings)
    fingerprint = split_hash(dataset_id, settings)
    if report is None or made is None or fingerprint is None:
        raise RecipeRefusedError(
            "The dataset has not been split yet. Run the Split step first, so evaluation "
            "never sees pictures the model trained on."
        )
    return RecipeSplit(
        mode=made.mode,
        seed=made.seed,
        val_fraction=made.val_fraction,
        test_fraction=made.test_fraction,
        sides={side: r.images for side, r in report.sides.items()},
        buffer=report.buffer,
        fingerprint=fingerprint,
    )


def save_recipe(
    dataset_id: str, request: RecipeRequest, settings: Settings | None = None
) -> Recipe:
    """Snapshot the dataset's preparation as a new recipe (or a new version of one)."""
    _validate(request)
    audit = last_audit(dataset_id, settings)
    if audit is None:
        raise RecipeRefusedError("The dataset has not been audited yet. Run the Audit step first.")
    state = load_state(dataset_id, settings)
    facts = collect(dataset_id, settings, state.class_map)
    current = facts_hash(facts)
    if audit.facts_hash != current:
        raise RecipeRefusedError(
            "The dataset changed after its last audit (images, annotations or fixes). Run "
            "the audit again, so the recipe describes the data it will train on."
        )
    split = _split(dataset_id, settings)
    plan = plan_input(facts, get_profile(request.target, settings), request.grid)
    tiling = plan.tiling
    same_name = [r for r in list_recipes(dataset_id, settings) if r.name == request.name]
    recipe = Recipe(
        id=uuid.uuid4().hex[:12],
        name=request.name,
        version=max((r.version for r in same_name), default=0) + 1,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        dataset_id=dataset_id,
        target=request.target,
        facts_hash=current,
        class_map=state.class_map,
        excluded=facts.excluded,
        split=split,
        fit=plan.fit,
        input_size=plan.input_size,
        tiling=RecipeTiling(columns=tiling.columns, rows=tiling.rows, overlap=tiling.overlap)
        if tiling.recommended
        else None,
        imbalance=request.imbalance,
        augmentation=request.augmentation,
        augment_copies=request.augment_copies,
        open_problems=[f.title for f in audit.findings if f.severity == "problem"],
        prompts=_prompts(dataset_id, settings) if request.target == "sam3" else None,
    )
    directory = dataset_dir(dataset_id, settings) / RECIPE_DIR
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{recipe.id}.json").write_text(recipe.model_dump_json(indent=2), encoding="utf-8")
    return recipe


def _prompts(dataset_id: str, settings: Settings | None) -> list[RecipePhrase]:
    from app.datasets.phrases import PhraseStore

    return [
        RecipePhrase(
            text=p.text,
            class_name=p.class_name,
            variants=p.variants,
            confusable=p.confusable,
            classes=p.classes if p.umbrella else [],
        )
        for p in PhraseStore(settings).list_for(dataset_id)
    ]


def check(recipe: Recipe, settings: Settings | None = None) -> list[str]:
    """What changed since the recipe was saved; empty when it still describes the data."""
    reasons = []
    state = load_state(recipe.dataset_id, settings)
    if state.class_map != recipe.class_map:
        reasons.append("The class map changed (Fix step).")
    facts = collect(recipe.dataset_id, settings, state.class_map)
    if facts_hash(facts) != recipe.facts_hash and not reasons:
        reasons.append("Images, annotations or exclusions changed since the recipe was saved.")
    if split_hash(recipe.dataset_id, settings) != recipe.split.fingerprint:
        reasons.append("The split changed since the recipe was saved.")
    return reasons


__all__ = [
    "Recipe",
    "RecipeRefusedError",
    "RecipeRequest",
    "check",
    "get_recipe",
    "list_recipes",
    "save_recipe",
]

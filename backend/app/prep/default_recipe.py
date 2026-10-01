"""The default recipe for a model (doc 101): Prepare data with every recommendation taken.

A recipe holds its dataset's split, so "a default recipe per model" is one dataset's
preparation for one model, made without questions: audit, leak-free split, the recommended
class balance and changed copies, the input plan's tiles — saved as "Default for <model>"
and refinable in Prepare data like any other recipe.
"""

from __future__ import annotations

from app.core.config import Settings
from app.ml.heads.registry import get_head_type
from app.prep.audit import facts_hash, last_audit, run_audit
from app.prep.augment_plan import plan_augmentation
from app.prep.balance_plan import plan_balance
from app.prep.jobs import PrepJob, Progress
from app.prep.profiles import PROFILES, ModelProfile, get_profile
from app.prep.recipe import Recipe, RecipeRequest, check, list_recipes, save_recipe
from app.prep.split_service import current_split, load_split_settings, make_split
from app.prep.state import load_state
from app.prep.stats import collect

_KNOWN = {profile.id for profile in PROFILES}
_TASKS = ("classification", "segmentation")


def profile_for(
    model_id: str, head_type_id: str | None = None, backbone_id: str | None = None
) -> str:
    """The preparation profile a model trains with. `ValueError` when there is none."""
    if model_id == "head":
        spec = get_head_type(head_type_id or "")
        if spec is None:
            raise ValueError(f"Unknown head type: {head_type_id}")
        return _head_profile(spec.task, backbone_id or "")
    if model_id in _KNOWN:
        return model_id
    for task in _TASKS:
        if model_id.startswith(("dinov2", "dinov3")) and model_id.endswith(f"-{task}"):
            return _head_profile(task, model_id)
    raise ValueError(f"No preparation recipe for {model_id}")


def _head_profile(task: str, backbone_id: str) -> str:
    family = "dinov3" if backbone_id.startswith("dinov3") else "dinov2"
    profile = f"head-{task}-{family}"
    if profile not in _KNOWN:
        raise ValueError(
            f"A {task} head has no preparation recipe: there is nothing to split or balance "
            "by class for it."
        )
    return profile


def default_name(profile: ModelProfile) -> str:
    return f"Default for {profile.label.removeprefix('Fine-tune ')}"


def _up_to_date_default(
    dataset_id: str, profile: ModelProfile, settings: Settings | None
) -> Recipe | None:
    name = default_name(profile)
    for recipe in reversed(list_recipes(dataset_id, settings)):
        if recipe.name == name and recipe.target == profile.id and not check(recipe, settings):
            return recipe
    return None


def _ensure_audit(
    dataset_id: str, target: str, progress: Progress, settings: Settings | None
) -> bool:
    """Audit when there is none, it is stale, or it judged another model. True if redone
    because the *data* changed — then the stored split no longer describes it either."""
    audit = last_audit(dataset_id, settings)
    facts = collect(dataset_id, settings, load_state(dataset_id, settings).class_map)
    stale = audit is not None and audit.facts_hash != facts_hash(facts)
    if audit is None or stale or audit.target != target:
        run_audit(dataset_id, target, progress, settings)
    return stale


def _ensure_split(dataset_id: str, data_changed: bool, settings: Settings | None) -> None:
    """Keep a split the user made unless the data changed since; otherwise make one."""
    made = load_split_settings(dataset_id, settings)
    stored = current_split(dataset_id, settings)
    if made is not None and stored is not None and not data_changed:
        return
    facts = collect(dataset_id, settings, load_state(dataset_id, settings).class_map)
    from_source = made is None and all(image.split for image in facts.images)
    make_split(dataset_id, mode="keep-source" if from_source else "auto", settings=settings)


def make_default_recipe(
    dataset_id: str, target: str, job: PrepJob, progress: Progress, settings: Settings | None = None
) -> Recipe:
    profile = get_profile(target, settings)
    existing = _up_to_date_default(dataset_id, profile, settings)
    if existing is not None:
        job.message = "An up-to-date default recipe already exists."
        return existing
    job.message = "Checking the data (audit)…"
    data_changed = _ensure_audit(dataset_id, target, progress, settings)
    job.message = "Splitting without leaks…"
    _ensure_split(dataset_id, data_changed, settings)
    job.message = "Choosing class balance and changed copies…"
    facts = collect(dataset_id, settings, load_state(dataset_id, settings).class_map)
    balance = plan_balance(facts, profile)
    augmentation = plan_augmentation(facts, profile)
    job.message = "Saving the recipe…"
    recipe = save_recipe(
        dataset_id,
        RecipeRequest(
            name=default_name(profile),
            target=target,
            imbalance=balance.recommended,
            augmentation=augmentation.recommended,
        ),
        settings,
    )
    job.message = f"Saved '{recipe.name}' v{recipe.version}."
    return recipe


__all__ = ["default_name", "make_default_recipe", "profile_for"]

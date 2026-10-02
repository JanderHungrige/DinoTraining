"""Does this dataset meet this model's requirements? Checked before a job starts (doc 92).

Each check names the rule, what was found, what is needed, and how to fix it, so a
refusal is something to act on rather than a dead end. The same result is the Training
tab's readiness list, the API's answer and the MCP tool's answer.
"""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.paths import is_installed, resolve_model_dir
from app.finetune.requirements import FinetuneRequirements, get_requirements
from app.ml.registry import get_model
from app.prep.recipe import check, get_recipe
from app.prep.state import load_state
from app.prep.stats import DatasetFacts, collect


class Check(BaseModel):
    id: str
    title: str
    passed: bool
    detail: str
    fix: str = ""


class Readiness(BaseModel):
    finetune_id: str
    dataset_id: str
    recipe_id: str | None
    ready: bool
    checks: list[Check]


def _counts(facts: DatasetFacts, spec: FinetuneRequirements) -> tuple[int, Counter[str]]:
    """Images that carry training data of the right kind, and instances per class."""
    if spec.annotation_kind == "image-labels":
        per_image: dict[int, set[str]] = {}
        for a in facts.positives():
            per_image.setdefault(a.image_id, set()).add(a.cls)
        single = [next(iter(c)) for c in per_image.values() if len(c) == 1]
        return len(single), Counter(single)
    kind = "box" if spec.annotation_kind == "boxes" else "mask"
    usable = [a for a in facts.positives() if a.kind == kind]
    return len({a.image_id for a in usable}), Counter(a.cls for a in usable)


def _model_checks(spec: FinetuneRequirements, settings: Settings) -> list[Check]:
    checks = [
        Check(
            id="available",
            title="This model can be fine-tuned here",
            passed=spec.available,
            detail="Yes." if spec.available else spec.unavailable_reason,
        )
    ]
    installed = is_installed(resolve_model_dir(spec.model_id, settings))
    model = get_model(spec.model_id)
    gated = model is not None and model.gated
    checks.append(
        Check(
            id="installed",
            title=f"{spec.label} is installed",
            passed=installed,
            detail="Installed." if installed else "Not downloaded yet.",
            fix=""
            if installed
            else "Download it in Models & Datasets"
            + (" (it is gated: set a HuggingFace token first)." if gated else "."),
        )
    )
    return checks


def _data_checks(spec: FinetuneRequirements, facts: DatasetFacts) -> list[Check]:
    images, per_class = _counts(facts, spec)
    kind = spec.annotation_kind.replace("-", " ")
    thin = {name: n for name, n in per_class.items() if n < spec.min_instances_per_class}
    return [
        Check(
            id="annotation-kind",
            title=f"The dataset has {kind}",
            passed=bool(per_class),
            detail=f"{sum(per_class.values())} found." if per_class else f"No {kind} found.",
            fix="" if per_class else spec.data_format,
        ),
        Check(
            id="images",
            title=f"At least {spec.min_images} images with {kind}",
            passed=images >= spec.min_images,
            detail=f"{images} images.",
            fix="" if images >= spec.min_images else "Annotate more images. " + spec.minimums_why,
        ),
        Check(
            id="per-class",
            title=f"At least {spec.min_instances_per_class} per class",
            passed=bool(per_class) and not thin,
            detail=", ".join(f"{name}: {n}" for name, n in sorted(per_class.items()))
            or "No classes.",
            fix=""
            if per_class and not thin
            else "Annotate more of: "
            + ", ".join(sorted(thin) or ["every class"])
            + ", or leave those classes out in Prepare data → Fix. "
            + spec.minimums_why,
        ),
    ]


def _recipe_check(
    spec: FinetuneRequirements, dataset_id: str, recipe_id: str | None, settings: Settings
) -> Check:
    title = "A preparation recipe" + (" (required)" if spec.recipe_required else "")
    if recipe_id is None:
        return Check(
            id="recipe",
            title=title,
            passed=not spec.recipe_required,
            detail="None given.",
            fix="Prepare data → save a recipe, then choose it here. Its leak-free split is "
            "what the base and fine-tuned models are compared on.",
        )
    recipe = get_recipe(dataset_id, recipe_id, settings)
    if recipe is None:
        return Check(id="recipe", title=title, passed=False, detail="No such recipe.")
    stale = check(recipe, settings)
    return Check(
        id="recipe",
        title=title,
        passed=not stale,
        detail=f"'{recipe.name}' v{recipe.version}" + (": " + " ".join(stale) if stale else "."),
        fix="Save the recipe again in Prepare data." if stale else "",
    )


def preflight(
    finetune_id: str,
    dataset_id: str,
    recipe_id: str | None = None,
    settings: Settings | None = None,
) -> Readiness:
    settings = settings or get_settings()
    spec = get_requirements(finetune_id)
    facts = collect(dataset_id, settings, load_state(dataset_id, settings).class_map)
    checks = [
        *_model_checks(spec, settings),
        *_data_checks(spec, facts),
        _recipe_check(spec, dataset_id, recipe_id, settings),
    ]
    return Readiness(
        finetune_id=finetune_id,
        dataset_id=dataset_id,
        recipe_id=recipe_id,
        ready=all(c.passed for c in checks),
        checks=checks,
    )


def refusal(readiness: Readiness) -> str:
    """The failed checks as one message, for a 409 or an MCP error."""
    failed = [c for c in readiness.checks if not c.passed]
    return " ".join(f"{c.title}: {c.detail} {c.fix}".strip() for c in failed)


__all__ = ["Check", "Readiness", "preflight", "refusal"]

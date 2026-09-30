"""A recipe, turned into the training fields that apply it (doc 90).

The one place that decides whether a recipe may be trained from: it must exist, still
describe the data (doc 88's check), and have been prepared for the same kind of model.
"""

from __future__ import annotations

from app.core.config import Settings
from app.prep.profiles import get_profile
from app.prep.recipe import Recipe, check, get_recipe


class RecipeOutOfDateError(ValueError):
    """The data changed since the recipe was saved; the message says what changed."""


def resolve_recipe(
    dataset_ids: list[str], recipe_id: str, task: str, settings: Settings | None = None
) -> Recipe:
    if len(dataset_ids) != 1:
        raise ValueError(
            "A recipe describes one dataset. Train on that dataset alone, or without a recipe."
        )
    recipe = get_recipe(dataset_ids[0], recipe_id, settings)
    if recipe is None:
        raise LookupError(f"No recipe {recipe_id} for dataset {dataset_ids[0]}")
    reasons = check(recipe, settings)
    if reasons:
        raise RecipeOutOfDateError(
            f"Recipe '{recipe.name}' v{recipe.version} no longer describes the data: "
            + " ".join(reasons)
            + " Save it again in the Prepare data tab."
        )
    prepared_for = get_profile(recipe.target, settings)
    if prepared_for.task != task:
        raise ValueError(
            f"Recipe '{recipe.name}' was prepared for {prepared_for.label} "
            f"({prepared_for.task}), not for a {task} model."
        )
    return recipe


def training_fields(recipe: Recipe) -> dict[str, object]:
    """What the recipe sets on a training run. The recipe id goes into the provenance."""
    tiles = max(recipe.tiling.columns, recipe.tiling.rows) if recipe.tiling else 0
    return {**recipe.training_fields(), "recipe_id": recipe.id, "tile_long_edge": tiles}


__all__ = ["RecipeOutOfDateError", "resolve_recipe", "training_fields"]

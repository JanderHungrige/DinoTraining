"""Preparation recipes: save, list and check (doc 88)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.datasets.store import DatasetStore
from app.prep.recipe import (
    Recipe,
    RecipeRefusedError,
    RecipeRequest,
    check,
    get_recipe,
    list_recipes,
    save_recipe,
)

router = APIRouter()


class RecipeInfo(BaseModel):
    recipe: Recipe
    #: Why the recipe no longer describes the data; empty when it does.
    out_of_date: list[str]


def _require(dataset_id: str) -> None:
    if not DatasetStore().exists(dataset_id):
        raise HTTPException(status_code=404, detail=f"Dataset not found: {dataset_id}")


@router.post(
    "/datasets/{dataset_id}/recipes",
    response_model=RecipeInfo,
    status_code=status.HTTP_201_CREATED,
    summary="Save the dataset's preparation as a recipe (a new version if the name exists)",
)
def create_recipe(dataset_id: str, request: RecipeRequest) -> RecipeInfo:
    _require(dataset_id)
    try:
        recipe = save_recipe(dataset_id, request)
    except RecipeRefusedError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except ValueError as error:  # the project's backstop: a validation failure is never a 500
        raise HTTPException(status_code=422, detail=str(error)) from error
    return RecipeInfo(recipe=recipe, out_of_date=[])


@router.get(
    "/datasets/{dataset_id}/recipes",
    response_model=list[RecipeInfo],
    summary="The dataset's recipes, oldest first, each checked against the data",
)
def get_recipes(dataset_id: str) -> list[RecipeInfo]:
    _require(dataset_id)
    return [RecipeInfo(recipe=r, out_of_date=check(r)) for r in list_recipes(dataset_id)]


@router.get(
    "/datasets/{dataset_id}/recipes/{recipe_id}",
    response_model=RecipeInfo,
    summary="One recipe, checked against the data",
)
def get_one(dataset_id: str, recipe_id: str) -> RecipeInfo:
    _require(dataset_id)
    recipe = get_recipe(dataset_id, recipe_id)
    if recipe is None:
        raise HTTPException(status_code=404, detail=f"No such recipe: {recipe_id}")
    return RecipeInfo(recipe=recipe, out_of_date=check(recipe))


__all__ = ["router"]

/**
 * The recipes of the one dataset a training run uses, and the one it follows (doc 90).
 * Loaded, never seeded: `choice` is only what the user picked.
 */

import { useEffect, useState } from 'react';

import { listRecipes, type RecipeInfo } from '../api/prepPlan';

export const NO_RECIPE = 'none';

/** The user's pick, or the latest recipe that still describes the data. */
export function effectiveRecipe(recipes: readonly RecipeInfo[], choice: string): RecipeInfo | null {
  if (choice === NO_RECIPE) return null;
  const usable = recipes.filter((info) => info.out_of_date.length === 0);
  return usable.find((info) => info.recipe.id === choice) ?? usable[usable.length - 1] ?? null;
}

export function useRecipeChoice(
  datasetIds: readonly string[],
  choice: string,
): { recipes: readonly RecipeInfo[]; chosen: RecipeInfo | null; error: string } {
  const single = datasetIds.length === 1 ? datasetIds[0]! : '';
  const [recipes, setRecipes] = useState<readonly RecipeInfo[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    setRecipes([]);
    setError('');
    if (!single) return;
    let live = true;
    listRecipes(single)
      .then((found) => live && setRecipes(found))
      .catch((cause: unknown) => live && setError(cause instanceof Error ? cause.message : String(cause)));
    return () => {
      live = false;
    };
  }, [single]);
  return { recipes, chosen: single ? effectiveRecipe(recipes, choice) : null, error };
}

/**
 * Which preparation recipe a training run follows (doc 90). Shown for a single dataset:
 * a recipe describes one.
 */

import type { JSX, ReactNode } from 'react';

import type { RecipeInfo } from '../api/prepPlan';
import { NO_RECIPE } from '../hooks/useRecipeChoice';

export interface RecipePickerProps {
  readonly datasetIds: readonly string[];
  readonly recipes: readonly RecipeInfo[];
  readonly chosen: RecipeInfo | null;
  readonly error: string;
  readonly onChoice: (choice: string) => void;
  /** Doc 101: shown instead of the one-line warning when no recipe is chosen. */
  readonly explainer?: ReactNode;
}

export function RecipePicker({
  datasetIds,
  recipes,
  chosen,
  error,
  onChoice,
  explainer,
}: RecipePickerProps): JSX.Element | null {
  if (datasetIds.length !== 1) return null;
  return (
    <div className="recipepicker">
      <label className="genpanel__field">
        <span>Preparation recipe</span>
        <select value={chosen?.recipe.id ?? NO_RECIPE} onChange={(event) => onChoice(event.target.value)}>
          <option value={NO_RECIPE}>None — train on the data as it is</option>
          {[...recipes].reverse().map(({ recipe, out_of_date: outOfDate }) => (
            <option key={recipe.id} value={recipe.id} disabled={outOfDate.length > 0}>
              {recipe.name} · v{recipe.version}
              {outOfDate.length > 0 ? ' (out of date)' : ''}
            </option>
          ))}
        </select>
      </label>
      {error && <p className="run__warn">{error}</p>}
      {chosen ? (
        <p className="trainer__hint">
          Uses the recipe&apos;s split, class changes, tiles, unequal-class handling (
          {chosen.recipe.imbalance}) and changed copies ({chosen.recipe.augmentation}).
        </p>
      ) : explainer ? (
        explainer
      ) : (
        <p className="run__warn">
          No recipe: the pictures are split at random, so near-identical ones may sit on both
          sides and the score may look better than the model is. The Prepare data tab makes a
          recipe.
        </p>
      )}
    </div>
  );
}

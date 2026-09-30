/**
 * Which preparation recipe a training run follows (doc 90). Shown for a single dataset:
 * a recipe describes one.
 */

import type { JSX, ReactNode } from 'react';

import type { RecipeInfo } from '../api/prepPlan';
import { NO_RECIPE } from '../hooks/useRecipeChoice';
import { useT } from '../i18n';

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
  const { t } = useT();
  if (datasetIds.length !== 1) return null;
  return (
    <div className="recipepicker">
      <label className="genpanel__field">
        <span>{t('training.recipe.label')}</span>
        <select value={chosen?.recipe.id ?? NO_RECIPE} onChange={(event) => onChoice(event.target.value)}>
          <option value={NO_RECIPE}>{t('training.recipe.none')}</option>
          {[...recipes].reverse().map(({ recipe, out_of_date: outOfDate }) => (
            <option key={recipe.id} value={recipe.id} disabled={outOfDate.length > 0}>
              {recipe.name} · v{recipe.version}
              {outOfDate.length > 0 ? ` ${t('training.recipe.outOfDate')}` : ''}
            </option>
          ))}
        </select>
      </label>
      {error && <p className="run__warn">{error}</p>}
      {chosen ? (
        <p className="trainer__hint">
          {t('training.recipe.uses', {
            imbalance: chosen.recipe.imbalance,
            augmentation: chosen.recipe.augmentation,
          })}
        </p>
      ) : explainer ? (
        explainer
      ) : (
        <p className="run__warn">{t('training.recipe.missing')}</p>
      )}
    </div>
  );
}

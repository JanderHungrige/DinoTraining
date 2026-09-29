/**
 * Step 8: review and save the recipe (doc 88). The server refuses with a reason when a
 * step is missing or the data changed since the audit; that reason is shown as it is.
 */

import { useState, type JSX } from 'react';

import { saveRecipe, type RecipeInfo, type Strategy } from '../../api/prepPlan';

export interface SaveChoices {
  readonly target: string;
  readonly targetLabel: string;
  readonly grid: number | null;
  readonly strategy: Strategy;
  readonly preset: string;
}

export interface SaveStepProps {
  readonly datasetId: string;
  readonly datasetName: string;
  readonly choices: SaveChoices;
  readonly recipes: readonly RecipeInfo[];
  readonly onSaved: () => void;
}

const STRATEGY_LABEL: Readonly<Record<Strategy, string>> = {
  none: 'left as they are',
  'weighted-loss': 'rare classes count more',
  'balanced-sampling': 'rare classes shown more often',
};

function RecipeList({ recipes }: { readonly recipes: readonly RecipeInfo[] }): JSX.Element {
  return (
    <ul className="prep-recipes">
      {[...recipes].reverse().map(({ recipe, out_of_date: outOfDate }) => (
        <li key={recipe.id} className={outOfDate.length ? 'prep-recipes__stale' : ''}>
          <strong>
            {recipe.name} · v{recipe.version}
          </strong>{' '}
          — {recipe.target}, {recipe.split.sides['train'] ?? 0}/{recipe.split.sides['val'] ?? 0}/
          {recipe.split.sides['test'] ?? 0} pictures, {recipe.imbalance}, {recipe.augmentation}
          {outOfDate.length > 0 && <span className="prep-recipes__why"> Out of date: {outOfDate.join(' ')}</span>}
        </li>
      ))}
    </ul>
  );
}

export function SaveStep({ datasetId, datasetName, choices, recipes, onSaved }: SaveStepProps): JSX.Element {
  const [nameOverride, setNameOverride] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const name = nameOverride || `${datasetName} for ${choices.targetLabel}`;
  const save = (): void => {
    setSaving(true);
    setError('');
    saveRecipe(datasetId, {
      name,
      target: choices.target,
      imbalance: choices.strategy,
      augmentation: choices.preset,
      grid: choices.grid,
    })
      .then(onSaved)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : String(cause)))
      .finally(() => setSaving(false));
  };
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        The recipe records everything decided here, so training uses exactly this preparation and a
        trained model can say how its data was prepared. Saving under the same name makes a new
        version; nothing is overwritten.
      </p>
      <ul className="prep-step__review">
        <li>Model: {choices.targetLabel}</li>
        <li>Tiles: {choices.grid === null ? 'as recommended' : choices.grid === 1 ? 'off' : `${choices.grid} along the long side`}</li>
        <li>Unequal classes: {STRATEGY_LABEL[choices.strategy]}</li>
        <li>Changed copies: {choices.preset === 'none' ? 'none' : choices.preset}</li>
      </ul>
      <label className="genpanel__field">
        <span>Recipe name</span>
        <input value={name} onChange={(event) => setNameOverride(event.target.value)} />
      </label>
      <button type="button" className="btn btn--primary" disabled={saving || !name.trim()} onClick={save}>
        Save the recipe
      </button>
      {error && <p className="admin__error" role="alert">{error}</p>}
      {recipes.length > 0 && <RecipeList recipes={recipes} />}
    </div>
  );
}

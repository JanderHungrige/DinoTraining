/**
 * Step 8: review and save the recipe (doc 88). The server refuses with a reason when a
 * step is missing or the data changed since the audit; that reason is shown as it is.
 */

import { useState, type JSX } from 'react';

import { saveRecipe, type RecipeInfo, type Strategy } from '../../api/prepPlan';
import { useT, type Key, type Translator } from '../../i18n';

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
  /** Doc 90: open Training with a recipe chosen. */
  readonly onTrain?: ((recipeId: string) => void) | undefined;
}

const STRATEGY_LABEL: Readonly<Record<Strategy, Key>> = {
  none: 'prepare.save.strategyNone',
  'weighted-loss': 'prepare.save.strategyWeighted',
  'balanced-sampling': 'prepare.save.strategyBalanced',
};

function tilesText(grid: number | null, t: Translator['t']): string {
  if (grid === null) return t('prepare.save.tilesRecommended');
  return grid === 1 ? t('prepare.save.tilesOff') : t('prepare.save.tilesGrid', { count: grid });
}

function RecipeList({ recipes }: { readonly recipes: readonly RecipeInfo[] }): JSX.Element {
  const { t } = useT();
  return (
    <ul className="prep-recipes">
      {[...recipes].reverse().map(({ recipe, out_of_date: outOfDate }) => (
        <li key={recipe.id} className={outOfDate.length ? 'prep-recipes__stale' : ''}>
          <strong>
            {recipe.name} · v{recipe.version}
          </strong>{' '}
          {t('prepare.save.recipeLine', {
            target: recipe.target,
            train: recipe.split.sides['train'] ?? 0,
            val: recipe.split.sides['val'] ?? 0,
            test: recipe.split.sides['test'] ?? 0,
            imbalance: recipe.imbalance,
            augmentation: recipe.augmentation,
          })}
          {outOfDate.length > 0 && (
            <span className="prep-recipes__why">{t('prepare.save.outOfDate', { reasons: outOfDate.join(' ') })}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function TrainButton(props: {
  readonly recipes: readonly RecipeInfo[];
  readonly target: string;
  readonly onTrain: (recipeId: string) => void;
}): JSX.Element | null {
  const { t } = useT();
  const latest = [...props.recipes]
    .reverse()
    .find((info) => info.recipe.target === props.target && info.out_of_date.length === 0);
  if (!latest) return null;
  return (
    <button type="button" className="btn btn--primary" onClick={() => props.onTrain(latest.recipe.id)}>
      {t('prepare.save.train', { name: latest.recipe.name, version: latest.recipe.version })}
    </button>
  );
}

export function SaveStep({ datasetId, datasetName, choices, recipes, onSaved, onTrain }: SaveStepProps): JSX.Element {
  const { t } = useT();
  const [nameOverride, setNameOverride] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const name = nameOverride || t('prepare.save.defaultName', { dataset: datasetName, model: choices.targetLabel });
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
        {t('prepare.save.why')}
      </p>
      <ul className="prep-step__review">
        <li>{t('prepare.save.model', { model: choices.targetLabel })}</li>
        <li>{t('prepare.save.tiles', { tiles: tilesText(choices.grid, t) })}</li>
        <li>{t('prepare.save.balance', { value: t(STRATEGY_LABEL[choices.strategy]) })}</li>
        <li>
          {t('prepare.save.augment', { value: choices.preset === 'none' ? t('prepare.save.augmentNone') : choices.preset })}
        </li>
      </ul>
      <label className="genpanel__field">
        <span>{t('prepare.save.name')}</span>
        <input value={name} onChange={(event) => setNameOverride(event.target.value)} />
      </label>
      <button type="button" className="btn btn--primary" disabled={saving || !name.trim()} onClick={save}>
        {t('prepare.save.button')}
      </button>
      {error && <p className="admin__error" role="alert">{error}</p>}
      {recipes.length > 0 && <RecipeList recipes={recipes} />}
      {onTrain && <TrainButton recipes={recipes} target={choices.target} onTrain={onTrain} />}
    </div>
  );
}

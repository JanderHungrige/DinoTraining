/**
 * "What is a recipe?" (doc 101), shown where a recipe can be chosen and none is.
 *
 * People who start in Training skip Prepare data; this is where they are told what they
 * skipped, what it costs, and offered both ways back: the model's default recipe in one
 * click, or Prepare data opened at this dataset and model.
 */

import { useState, type JSX } from 'react';

import { resolveTarget, type ModelRef } from '../api/defaultRecipe';
import type { Recipe } from '../api/prepPlan';
import { useDefaultRecipe } from '../hooks/useDefaultRecipe';
import { useT } from '../i18n';
import { writePersisted } from '../lib/persisted';
import '../params.css';

export interface RecipeExplainerProps {
  readonly datasetId: string;
  /** The model to prepare for; null while it is not chosen yet. */
  readonly model: ModelRef | null;
  /** Why `model` is null, e.g. "Choose a head type first." */
  readonly modelMissing?: string;
  /** A recipe is required to start (SAM, DINO backbones), not only recommended. */
  readonly required?: boolean;
  readonly onSaved: (recipe: Recipe) => void;
  readonly onOpenPrepare?: (() => void) | undefined;
}

export function RecipeExplainer(props: RecipeExplainerProps): JSX.Element {
  const { t } = useT();
  const { datasetId, model } = props;
  const recipe = useDefaultRecipe(datasetId, model, props.onSaved);
  const [openError, setOpenError] = useState('');

  const openPrepare = (): void => {
    if (!model || !props.onOpenPrepare) return;
    const navigate = props.onOpenPrepare;
    resolveTarget(model)
      .then(({ target }) => {
        // Prepare data opens at what it remembers (doc 69): set that, then go.
        writePersisted('prepare.dataset', datasetId);
        writePersisted('prepare.target', target);
        navigate();
      })
      .catch((cause: unknown) => setOpenError(cause instanceof Error ? cause.message : String(cause)));
  };

  return (
    <section className="recipe-explainer" aria-labelledby="recipe-explainer-title">
      <h4 id="recipe-explainer-title" className="recipe-explainer__title">
        {t('training.explainer.title')}
        {props.required ? ` ${t('training.explainer.required')}` : ''}
      </h4>
      <p>
        {t('training.explainer.whatBefore')} <strong>{t('training.explainer.whatStrong')}</strong>
        {t('training.explainer.whatAfter')}
      </p>
      <p>
        {t('training.explainer.whyBefore')} <strong>{t('training.explainer.whyStrong')}</strong>
        {t('training.explainer.whyAfter')}
      </p>
      <div className="recipe-explainer__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={!model || recipe.busy}
          onClick={recipe.create}
        >
          {recipe.busy ? t('training.explainer.making') : t('training.explainer.create')}
        </button>
        {props.onOpenPrepare && (
          <button type="button" className="btn" disabled={!model} onClick={openPrepare}>
            {t('training.explainer.openPrepare')}
          </button>
        )}
        {!model && props.modelMissing && <span className="trainer__dim">{props.modelMissing}</span>}
      </div>
      {recipe.busy && (
        <p role="status" className="trainer__dim">
          {recipe.message}
        </p>
      )}
      {[recipe.error, openError].filter(Boolean).map((text) => (
        <p key={text} className="run__warn" role="alert">
          {text}
        </p>
      ))}
    </section>
  );
}

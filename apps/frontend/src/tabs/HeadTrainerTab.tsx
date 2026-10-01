/**
 * Training — configure a run, watch it live, keep the result.
 *
 * **Two modes, switched by a control rather than by scrolling.** Fine-tuning used to sit
 * at the bottom of this tab under an `<h3>`, below the head form, the progress panel and
 * the list of trained heads — which meant that the model that actually wins at detection
 * (RF-DETR: 0.62 test mAP against 0.41 for a DINO head, leak-free split) was the one nobody found.
 * A tab called "Head Trainer" naming only half of what it did did not help.
 *
 * The two are genuinely different things, not two forms of one: a head trains against a
 * frozen backbone and is stored as weights beside a `backbone_id`; a fine-tune adapts a
 * whole model and is stored as one. Doc 55 is the long version of why that distinction is
 * load-bearing rather than an implementation detail.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { listHeadInstances, deleteHeadInstance, type HeadInstanceInfo } from '../api/headInstances';
import { FoundationFinetunePanel } from '../components/finetune/FoundationFinetunePanel';
import { HeadInstanceList } from '../components/HeadInstanceList';
import { RecipeExplainer } from '../components/RecipeExplainer';
import { RecipePicker } from '../components/RecipePicker';
import { TrainerForm, type TrainerSelection } from '../components/TrainerForm';
import { blockingParameter, ParameterForm } from '../components/params/ParameterForm';
import { useParameters } from '../hooks/useParameters';
import { useRecipeChoice } from '../hooks/useRecipeChoice';
import type { TrainRequest } from '../types/navigation';
import { usePersistentState } from '../hooks/usePersistentState';
import { isOneOf, isShapeOf, stillListed } from '../lib/persisted';
import { TrainingProgress } from '../components/TrainingProgress';
import { DatasetFormatPanel } from '../components/DatasetFormatPanel';
import { installedOnly, useTrainerOptions } from '../hooks/useTrainerOptions';
import { useTrainingRun } from '../hooks/useTrainingRun';
import { useT, type Key } from '../i18n';

/** The two things this tab does, and the one-line reason to pick each (catalogue keys). */
const MODES: readonly { id: TrainingMode; name: Key; hint: Key }[] = Object.freeze([
  { id: 'head', name: 'training.mode.head.name', hint: 'training.mode.head.hint' },
  { id: 'finetune', name: 'training.mode.finetune.name', hint: 'training.mode.finetune.hint' },
]);

const DEFAULTS: TrainerSelection = {
  datasetIds: [],
  backboneId: '',
  headTypeId: '',
  // Rounds, learning speed and the rest are doc 99's catalogue now (doc 100): the
  // defaults live in one place, the backend, and cannot drift from a copy here.
};

/** Which of the two things this tab does. */
type TrainingMode = 'head' | 'finetune';

const isTrainingMode = isOneOf<TrainingMode>(['head', 'finetune']);

export function HeadTrainerTab({
  request = null,
  onOpenPrepare,
}: {
  readonly request?: TrainRequest | null;
  /** Doc 101: "Open Prepare data" from the recipe explainer. */
  readonly onOpenPrepare?: () => void;
}): JSX.Element {
  const { t } = useT();
  // Defaults to the head path: it is the cheaper one, the one the rest of the app is
  // built around, and the one a first-time user has the data for.
  // Doc 69: the mode and the whole selection are remembered across tab switches.
  const [mode, setMode] = usePersistentState<TrainingMode>('trainer.mode', 'head', isTrainingMode);
  const [selection, setSelection] = usePersistentState<TrainerSelection>(
    'trainer.selection',
    DEFAULTS,
    isShapeOf(DEFAULTS),
  );
  // Doc 90: '' follows the latest up-to-date recipe, 'none' is none, else a recipe id.
  const [recipeChoice, setRecipeChoice] = useState('');
  // "Train with this recipe" from Prepare data is an instruction, not a default: it wins
  // over what was remembered, and pressing it again applies again (the nonce).
  useEffect(() => {
    if (!request) return;
    setMode('head');
    setSelection((current) => ({ ...current, datasetIds: [request.datasetId] }));
    setRecipeChoice(request.recipeId);
  }, [request, setMode, setSelection]);
  const [heads, setHeads] = useState<readonly HeadInstanceInfo[]>([]);
  const [busy, setBusy] = useState<Record<string, boolean>>({});

  const refreshHeads = useCallback(async (): Promise<void> => {
    try {
      setHeads(await listHeadInstances());
    } catch {
      // A failed head list must not hide the trainer itself.
    }
  }, []);

  const { datasets, backbones, headTypes, loading, error } = useTrainerOptions(
    selection.backboneId || null,
  );
  const run = useTrainingRun({ onComplete: () => void refreshHeads() });
  const params = useParameters('head');

  useEffect(() => {
    void refreshHeads();
  }, [refreshHeads]);

  const installed = installedOnly(backbones);
  const recipes = useRecipeChoice(selection.datasetIds, recipeChoice);
  const recipeId = recipes.chosen?.recipe.id ?? '';

  // What the remembered selection still refers to. A dataset, backbone or head type may be
  // gone since it was remembered; the form and the run see only what still exists, while
  // the stored selection keeps the rest in case a list merely failed to load.
  const live: TrainerSelection = {
    ...selection,
    datasetIds: selection.datasetIds.filter((id) => datasets.some((entry) => entry.id === id)),
    backboneId: stillListed(selection.backboneId, installed.map((entry) => entry.id)),
    headTypeId: stillListed(selection.headTypeId, headTypes.map((entry) => entry.id)),
  };

  // Preselect the only installed backbone: making the user pick from a list of one is
  // friction with no decision in it.
  useEffect(() => {
    if (!live.backboneId && installed.length === 1) {
      setSelection((current) => ({ ...current, backboneId: installed[0]!.id }));
    }
  }, [installed, live.backboneId, setSelection]);

  const remove = async (id: string): Promise<void> => {
    setBusy((current) => ({ ...current, [id]: true }));
    try {
      await deleteHeadInstance(id);
      await refreshHeads();
    } finally {
      setBusy((current) => ({ ...current, [id]: false }));
    }
  };

  return (
    <section className="trainer">
      <h2 className="trainer__title">{t('training.tab.title')}</h2>

      {/* Radios, not tabs-within-tabs: two mutually exclusive things, and a radio group
          says that to a screen reader without any ARIA being written by hand. */}
      <fieldset className="modeswitch">
        <legend className="modeswitch__legend">{t('training.mode.legend')}</legend>
        {MODES.map((entry) => (
          <label
            key={entry.id}
            className={`modeswitch__option${mode === entry.id ? ' modeswitch__option--on' : ''}`}
          >
            <input
              type="radio"
              name="training-mode"
              value={entry.id}
              checked={mode === entry.id}
              onChange={() => setMode(entry.id)}
            />
            <span className="modeswitch__name">{t(entry.name)}</span>
            <span className="modeswitch__hint">{t(entry.hint)}</span>
          </label>
        ))}
      </fieldset>

      {error && <p className="run__warn">{error}</p>}
      {loading && <p className="trainer__dim">{t('training.tab.loadingOptions')}</p>}

      {mode === 'finetune' ? (
        <>
          <p className="trainer__hint">{t('training.tab.finetuneIntro')}</p>
          <FoundationFinetunePanel datasets={datasets} onOpenPrepare={onOpenPrepare} />
        </>
      ) : (
        <>
          <p className="trainer__hint">{t('training.tab.headIntro')}</p>

          {/* Beside the form rather than in the docs tab: the question is asked *while*
              filling this in, by someone who has just downloaded a dataset from somewhere
              and wants to know whether it will load. */}
          <DatasetFormatPanel />

          <RecipePicker
            datasetIds={live.datasetIds}
            {...recipes}
            onChoice={setRecipeChoice}
            explainer={
              <RecipeExplainer
                datasetId={live.datasetIds[0] ?? ''}
                model={
                  live.headTypeId && live.backboneId
                    ? { model_id: 'head', head_type_id: live.headTypeId, backbone_id: live.backboneId }
                    : null
                }
                modelMissing={t('training.tab.modelMissing')}
                onSaved={(saved) => {
                  setRecipeChoice(saved.id);
                  recipes.reload();
                }}
                onOpenPrepare={onOpenPrepare}
              />
            }
          />

          <TrainerForm
            datasets={datasets}
            backbones={installed}
            headTypes={headTypes}
            value={live}
            disabled={run.running}
            starting={run.starting}
            onChange={setSelection}
            settings={<ParameterForm params={params} recipeChosen={Boolean(recipeId)} disabled={run.running} />}
            settingsProblem={params.set ? blockingParameter(params) : t('training.params.loading')}
            onSubmit={() =>
              void run.start({
                head_type_id: live.headTypeId,
                backbone_id: live.backboneId,
                dataset_ids: live.datasetIds,
                ...params.values,
                ...(recipeId ? { recipe_id: recipeId } : {}),
              })
            }
          />

          {run.error && <p className="run__warn">{run.error}</p>}

          {run.job && (
            <TrainingProgress
              job={run.job}
              history={run.history}
              onCancel={() => void run.cancel()}
            />
          )}

          <h3 className="trainer__subtitle">{t('training.tab.trainedHeads')}</h3>
          <HeadInstanceList heads={heads} busy={busy} onDelete={(id) => void remove(id)} />
        </>
      )}
    </section>
  );
}

/**
 * Fine-tune a foundation model (doc 97): pick the model, read what it needs, check the
 * data against it, and only then train. Replaces doc 44's RF-DETR-only panel: RF-DETR is
 * one entry of doc 92's contract now, beside SAM 2, SAM 3 and the DINO backbones.
 *
 * Choices are remembered (doc 69) and read through `stillListed`; the model list, the
 * readiness and the recipes are loaded, never seeded into state.
 */

import { useEffect, useState, type JSX } from 'react';

import type { DatasetInfo } from '../../api/datasets';
import { listRequirements, type FinetuneRequirements } from '../../api/finetune';
import { useFoundationFinetune, useReadiness, type FoundationFinetune } from '../../hooks/useFoundationFinetune';
import { usePersistentState } from '../../hooks/usePersistentState';
import { useRecipeChoice } from '../../hooks/useRecipeChoice';
import { finetuneFields, useParameters } from '../../hooks/useParameters';
import { useT } from '../../i18n';
import { isString, stillListed } from '../../lib/persisted';
import { blockingParameter, ParameterForm } from '../params/ParameterForm';
import { RecipeExplainer } from '../RecipeExplainer';
import { RecipePicker } from '../RecipePicker';
import { FinetuneResult, ReadinessList, RequirementsCard } from './FinetuneParts';
import '../../finetune.css';

function useRequirements(): { specs: readonly FinetuneRequirements[]; error: string } {
  const [specs, setSpecs] = useState<readonly FinetuneRequirements[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    let live = true;
    listRequirements()
      .then((found) => live && setSpecs(found))
      .catch((cause: unknown) => live && setError(cause instanceof Error ? cause.message : String(cause)));
    return () => {
      live = false;
    };
  }, []);
  return { specs, error };
}

function Pickers(props: {
  readonly specs: readonly FinetuneRequirements[];
  readonly datasets: readonly DatasetInfo[];
  readonly modelId: string;
  readonly datasetId: string;
  readonly onModel: (id: string) => void;
  readonly onDataset: (id: string) => void;
}): JSX.Element {
  const { t, tp } = useT();
  return (
    <div className="inspect__pickers">
      <label className="genpanel__field">
        <span>{t('training.finetune.model')}</span>
        <select value={props.modelId} onChange={(e) => props.onModel(e.target.value)}>
          {props.specs.map((s) => (
            <option key={s.id} value={s.id} disabled={!s.available}>
              {s.label}
              {s.available ? '' : ` ${t('training.finetune.notYet')}`}
            </option>
          ))}
        </select>
      </label>
      <label className="genpanel__field">
        <span>{t('training.finetune.dataset')}</span>
        <select value={props.datasetId} onChange={(e) => props.onDataset(e.target.value)}>
          {props.datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name} ({tp('common.pictures', d.counts.images)})
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function RunControls(props: {
  readonly ready: boolean;
  readonly blocked: string;
  readonly run: FoundationFinetune;
  readonly onStart: () => void;
}): JSX.Element {
  const { t } = useT();
  const { run } = props;
  const job = run.job;
  return (
    <>
      <div className="prep-step__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={!props.ready || Boolean(props.blocked) || run.starting || run.running}
          onClick={props.onStart}
        >
          {run.starting ? t('training.finetune.starting') : t('training.finetune.start')}
        </button>
        {props.blocked && <span className="trainer__blocked">{props.blocked}</span>}
        {run.running && (
          <button type="button" className="btn" onClick={() => void run.cancel()}>
            {t('common.cancel')}
          </button>
        )}
      </div>
      {job && (
        <p role="status" className="prep-step__status">
          {job.state === 'running' || job.state === 'pending'
            ? t(job.epoch === 0 ? 'training.finetune.roundBase' : 'training.finetune.round', {
                epoch: job.epoch,
                total: job.total_epochs,
              })
            : job.message}
        </p>
      )}
    </>
  );
}

export function FoundationFinetunePanel({
  datasets,
  onOpenPrepare,
}: {
  readonly datasets: readonly DatasetInfo[];
  /** Doc 101: "Open Prepare data" from the recipe explainer. */
  readonly onOpenPrepare?: (() => void) | undefined;
}): JSX.Element {
  const { t } = useT();
  const { specs, error: listError } = useRequirements();
  const [modelChoice, setModelChoice] = usePersistentState('finetune.model', '', isString);
  const [datasetChoice, setDatasetChoice] = usePersistentState('finetune.dataset', '', isString);
  const [nameOverride, setNameOverride] = useState('');
  const [recipeChoice, setRecipeChoice] = useState('');
  const withImages = datasets.filter((d) => d.counts.images > 0);
  const modelId = stillListed(modelChoice, specs.map((s) => s.id)) || specs.find((s) => s.available)?.id || '';
  const datasetId = stillListed(datasetChoice, withImages.map((d) => d.id)) || withImages[0]?.id || '';
  const spec = specs.find((s) => s.id === modelId) ?? null;
  const recipes = useRecipeChoice(datasetId ? [datasetId] : [], recipeChoice);
  const recipeId = recipes.chosen?.recipe.id ?? '';
  const { readiness, error: checkError } = useReadiness(modelId, datasetId, recipeId);
  const run = useFoundationFinetune();
  const dataset = withImages.find((d) => d.id === datasetId);
  const name = nameOverride || `${dataset?.name ?? 'dataset'} · ${spec?.label ?? ''}`;
  // Doc 100: every setting comes from the model's catalogue (doc 99), defaults included —
  // no hand-written rounds, blocks or learning rate here any more.
  const params = useParameters(modelId);
  const blocked = params.set ? blockingParameter(params) : t('training.params.loading');

  const start = (): void => {
    void run.start({
      finetune_id: modelId,
      dataset_ids: [datasetId],
      name,
      ...(recipeId ? { recipe_id: recipeId } : {}),
      ...finetuneFields(params.values),
    });
  };

  return (
    <div className="ft">
      <Pickers
        specs={specs}
        datasets={withImages}
        modelId={modelId}
        datasetId={datasetId}
        onModel={setModelChoice}
        onDataset={setDatasetChoice}
      />
      {[listError, checkError, run.error].filter(Boolean).map((e) => (
        <p key={e} className="admin__error" role="alert">
          {e}
        </p>
      ))}
      {spec && <RequirementsCard spec={spec} />}
      <RecipePicker
        datasetIds={datasetId ? [datasetId] : []}
        {...recipes}
        onChoice={setRecipeChoice}
        explainer={
          <RecipeExplainer
            datasetId={datasetId}
            model={modelId ? { model_id: modelId } : null}
            required={spec?.recipe_required ?? false}
            onSaved={(saved) => {
              setRecipeChoice(saved.id);
              recipes.reload();
            }}
            onOpenPrepare={onOpenPrepare}
          />
        }
      />
      {readiness && <ReadinessList readiness={readiness} />}
      <ParameterForm params={params} disabled={run.running} />
      <label className="genpanel__field">
        <span>{t('training.finetune.name')}</span>
        <input value={name} onChange={(e) => setNameOverride(e.target.value)} />
      </label>
      <RunControls
        ready={Boolean(readiness?.ready)}
        blocked={blocked}
        run={run}
        onStart={start}
      />
      {run.job && !run.running && run.job.state === 'complete' && <FinetuneResult job={run.job} />}
    </div>
  );
}

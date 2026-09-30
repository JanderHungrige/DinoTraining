/**
 * Prepare data (doc 89): a guided path from a dataset to a saved recipe, for people who
 * have never trained a model. Every step has a recommended default and says why; experts
 * can go straight to any step.
 *
 * The choices (tiles, unequal classes, changed copies) are *overrides* of the loaded
 * recommendation, never state seeded from it: they belong to one dataset and model, and
 * a different pair starts from its own recommendations again.
 */

import { useEffect, useState, type JSX } from 'react';

import { listDatasets, type DatasetInfo } from '../api/datasets';
import { listTargets, type PrepTarget } from '../api/prep';
import { PrepareSteps, type Choices } from '../components/prepare/PrepareSteps';
import { usePersistentState } from '../hooks/usePersistentState';
import { usePrepareData } from '../hooks/usePrepareData';
import { usePreparePlans } from '../hooks/usePreparePlans';
import { useT } from '../i18n';
import { isString, stillListed } from '../lib/persisted';
import '../prepare.css';

function useLists(): { datasets: readonly DatasetInfo[]; targets: readonly PrepTarget[]; error: string } {
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [targets, setTargets] = useState<readonly PrepTarget[]>([]);
  const [error, setError] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    // An aborted request (the effect cleaned up, as StrictMode does once on mount) reports
    // itself as "cannot reach the backend". It is not an error, and must not say so.
    const fail = (cause: unknown): void => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : String(cause));
    };
    listDatasets(controller.signal).then(setDatasets, fail);
    listTargets().then((found) => !controller.signal.aborted && setTargets(found), fail);
    return () => controller.abort();
  }, []);
  return { datasets, targets, error };
}

function Pickers(props: {
  readonly datasets: readonly DatasetInfo[];
  readonly targets: readonly PrepTarget[];
  readonly datasetId: string;
  readonly target: string;
  readonly onDataset: (id: string) => void;
  readonly onTarget: (id: string) => void;
}): JSX.Element {
  const { datasets, targets, datasetId, target, onDataset, onTarget } = props;
  const { t, tp } = useT();
  return (
      <div className="inspect__pickers">
        <label className="genpanel__field">
          <span>{t('prepare.tab.dataset')}</span>
          <select value={datasetId} onChange={(event) => onDataset(event.target.value)}>
            {datasets.length === 0 && <option value="">{t('prepare.tab.noDatasets')}</option>}
            {datasets.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {tp('prepare.tab.datasetOption', entry.counts.images, { name: entry.name })}
              </option>
            ))}
          </select>
        </label>
        <label className="genpanel__field">
          <span>{t('prepare.tab.model')}</span>
          <select value={target} onChange={(event) => onTarget(event.target.value)}>
            {targets.map((entry) => (
              <option key={entry.id} value={entry.id}>
                {entry.label}
              </option>
            ))}
          </select>
        </label>
      </div>
  );
}

export function PrepareTab({
  onTrain,
}: {
  readonly onTrain?: ((datasetId: string, recipeId: string) => void) | undefined;
}): JSX.Element {
  const { t } = useT();
  const lists = useLists();
  const [datasetChoice, setDatasetChoice] = usePersistentState('prepare.dataset', '', isString);
  const [targetChoice, setTargetChoice] = usePersistentState('prepare.target', '', isString);
  const withImages = lists.datasets.filter((entry) => entry.counts.images > 0);
  const datasetId = stillListed(datasetChoice, withImages.map((entry) => entry.id)) || withImages[0]?.id || '';
  const target = stillListed(targetChoice, lists.targets.map((entry) => entry.id)) || lists.targets[0]?.id || '';
  const data = usePrepareData(datasetId);
  const version = `${data.audit?.created_at ?? ''}|${JSON.stringify(data.state?.class_map ?? {})}`;
  const plans = usePreparePlans(datasetId, target, version);
  const [choices, setChoices] = useState<Choices>({ key: '' });
  const key = `${datasetId}:${target}`;
  const own = choices.key === key ? choices : { key };
  const choose = (change: Omit<Choices, 'key'>): void => setChoices({ ...own, ...change, key });

  return (
    <section className="studio prep">
      <h2 className="studio__title">{t('prepare.tab.title')}</h2>
      <p className="studio__lead">{t('prepare.tab.lead')}</p>
      <Pickers
        datasets={withImages}
        targets={lists.targets}
        datasetId={datasetId}
        target={target}
        onDataset={setDatasetChoice}
        onTarget={setTargetChoice}
      />
      {[lists.error, data.error, plans.error].filter(Boolean).map((error) => (
        <p key={error} className="admin__error" role="alert">
          {error}
        </p>
      ))}
      {datasetId && target && (
        <PrepareSteps
          datasetId={datasetId}
          datasetName={withImages.find((entry) => entry.id === datasetId)?.name ?? ''}
          target={lists.targets.find((entry) => entry.id === target) ?? null}
          data={data}
          plans={plans}
          choices={own}
          onChoose={choose}
          onTrain={onTrain}
        />
      )}
    </section>
  );
}

/** Wave 2 — Head Trainer: configure a run, watch it live, keep the result. */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { listHeadInstances, deleteHeadInstance, type HeadInstanceInfo } from '../api/headInstances';
import { FinetunePanel } from '../components/FinetunePanel';
import { HeadInstanceList } from '../components/HeadInstanceList';
import { TrainerForm, type TrainerSelection } from '../components/TrainerForm';
import { TrainingProgress } from '../components/TrainingProgress';
import { DatasetFormatPanel } from '../components/DatasetFormatPanel';
import { listFoundations, type FoundationInfo } from '../api/foundation';
import { useFinetune } from '../hooks/useFinetune';
import { installedOnly, useTrainerOptions } from '../hooks/useTrainerOptions';
import { useTrainingRun } from '../hooks/useTrainingRun';

const DEFAULTS: TrainerSelection = {
  datasetIds: [],
  backboneId: '',
  headTypeId: '',
  // Mirrors TrainingConfig's defaults so the form and the backend agree on "good
  // defaults" — two sets of defaults is how a UI quietly trains something else.
  epochs: 20,
  learningRate: 0.001,
  earlyStoppingPatience: 5,
};

export function HeadTrainerTab(): JSX.Element {
  const [selection, setSelection] = useState<TrainerSelection>(DEFAULTS);
  const [foundations, setFoundations] = useState<readonly FoundationInfo[]>([]);
  const finetune = useFinetune();

  useEffect(() => {
    const controller = new AbortController();
    // Non-fatal: head training still works if the catalogue is unhappy.
    void listFoundations(controller.signal)
      .then(setFoundations)
      .catch(() => undefined);
    return () => controller.abort();
  }, [finetune.job?.instance_id]);
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

  useEffect(() => {
    void refreshHeads();
  }, [refreshHeads]);

  const installed = installedOnly(backbones);

  // Preselect the only installed backbone: making the user pick from a list of one is
  // friction with no decision in it.
  useEffect(() => {
    if (!selection.backboneId && installed.length === 1) {
      setSelection((current) => ({ ...current, backboneId: installed[0]!.id }));
    }
  }, [installed, selection.backboneId]);

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
      <h2 className="trainer__title">Head Trainer</h2>
      <p className="trainer__hint">
        The backbone stays frozen — only the head trains. Preprocessing is chosen from the
        backbone and head type for you.
      </p>

      {/* Beside the form rather than in the docs tab: the question is asked *while*
          filling this in, by someone who has just downloaded a dataset from somewhere
          and wants to know whether it will load. */}
      <DatasetFormatPanel />

      {error && <p className="run__warn">{error}</p>}
      {loading && <p className="trainer__dim">Loading options…</p>}

      <TrainerForm
        datasets={datasets}
        backbones={installed}
        headTypes={headTypes}
        value={selection}
        disabled={run.running}
        starting={run.starting}
        onChange={setSelection}
        onSubmit={() =>
          void run.start({
            head_type_id: selection.headTypeId,
            backbone_id: selection.backboneId,
            dataset_ids: selection.datasetIds,
            epochs: selection.epochs,
            learning_rate: selection.learningRate,
            early_stopping_patience: selection.earlyStoppingPatience,
          })
        }
      />

      {run.error && <p className="run__warn">{run.error}</p>}

      {run.job && (
        <TrainingProgress job={run.job} history={run.history} onCancel={() => void run.cancel()} />
      )}

      <h3 className="trainer__subtitle">Fine-tune a general detector</h3>
      <FinetunePanel
        datasets={datasets}
        foundations={foundations}
        job={finetune.job}
        starting={finetune.starting}
        running={finetune.running}
        error={finetune.error}
        onStart={(options) => void finetune.start(options)}
        onCancel={() => void finetune.cancel()}
      />

      <h3 className="trainer__subtitle">Trained heads</h3>
      <HeadInstanceList heads={heads} busy={busy} onDelete={(id) => void remove(id)} />
    </section>
  );
}

/**
 * Training — configure a run, watch it live, keep the result.
 *
 * **Two modes, switched by a control rather than by scrolling.** Fine-tuning used to sit
 * at the bottom of this tab under an `<h3>`, below the head form, the progress panel and
 * the list of trained heads — which meant that the model that actually wins at detection
 * (RF-DETR, 0.96 mAP on rail against 0.5-0.6 for a DINO head) was the one nobody found.
 * A tab called "Head Trainer" naming only half of what it did did not help.
 *
 * The two are genuinely different things, not two forms of one: a head trains against a
 * frozen backbone and is stored as weights beside a `backbone_id`; a fine-tune adapts a
 * whole model and is stored as one. Doc 55 is the long version of why that distinction is
 * load-bearing rather than an implementation detail.
 */

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

/** The two things this tab does, and the one-line reason to pick each. */
const MODES: readonly { id: TrainingMode; name: string; hint: string }[] = Object.freeze([
  {
    id: 'head',
    name: 'DINO head',
    hint: 'Frozen backbone, trains in minutes. Best for classification and segmentation.',
  },
  {
    id: 'finetune',
    name: 'Fine-tune a model',
    hint: 'Adapts a whole detector. Slower, and much stronger at boxes.',
  },
]);

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

/** Which of the two things this tab does. */
type TrainingMode = 'head' | 'finetune';

export function HeadTrainerTab(): JSX.Element {
  // Defaults to the head path: it is the cheaper one, the one the rest of the app is
  // built around, and the one a first-time user has the data for.
  const [mode, setMode] = useState<TrainingMode>('head');
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
      <h2 className="trainer__title">Training</h2>

      {/* Radios, not tabs-within-tabs: two mutually exclusive things, and a radio group
          says that to a screen reader without any ARIA being written by hand. */}
      <fieldset className="modeswitch">
        <legend className="modeswitch__legend">What to train</legend>
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
            <span className="modeswitch__name">{entry.name}</span>
            <span className="modeswitch__hint">{entry.hint}</span>
          </label>
        ))}
      </fieldset>

      {error && <p className="run__warn">{error}</p>}
      {loading && <p className="trainer__dim">Loading options…</p>}

      {mode === 'finetune' ? (
        <>
          <p className="trainer__hint">
            Trains the whole model on your classes, weights and all — not a head on top of
            a frozen one. Slower, and much stronger at detection: measured here at mAP 0.96
            on rail against 0.5–0.6 for a DINO head on the same data.
          </p>
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
        </>
      ) : (
        <>
          <p className="trainer__hint">
            The backbone stays frozen — only the head trains. Preprocessing is chosen from
            the backbone and head type for you.
          </p>

          {/* Beside the form rather than in the docs tab: the question is asked *while*
              filling this in, by someone who has just downloaded a dataset from somewhere
              and wants to know whether it will load. */}
          <DatasetFormatPanel />

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
            <TrainingProgress
              job={run.job}
              history={run.history}
              onCancel={() => void run.cancel()}
            />
          )}

          <h3 className="trainer__subtitle">Trained heads</h3>
          <HeadInstanceList heads={heads} busy={busy} onDelete={(id) => void remove(id)} />
        </>
      )}
    </section>
  );
}

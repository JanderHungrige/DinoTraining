/**
 * Fine-tune a general detector on your own datasets (doc 44 UI).
 *
 * Lives in the Head Trainer because that is where training lives, but says plainly that it
 * is a *different* kind of training: minutes rather than seconds, one large model rather
 * than a small head. The Trainer's own hint says the backbone stays frozen — that is true
 * here too, and the panel proves it by reporting the frozen/trainable split the API
 * returns rather than asserting it.
 */

import { useState, type JSX } from 'react';

import type { DatasetInfo } from '../api/datasets';
import type { FinetuneJob, FoundationInfo } from '../api/foundation';
import { FieldHint } from './FieldHint';

export interface FinetunePanelProps {
  readonly datasets: readonly DatasetInfo[];
  readonly foundations: readonly FoundationInfo[];
  readonly job: FinetuneJob | null;
  readonly starting: boolean;
  readonly running: boolean;
  readonly error: string | null;
  readonly onStart: (options: {
    foundationId: string;
    datasetIds: string[];
    name: string;
    epochs: number;
    learningRate: number;
  }) => void;
  readonly onCancel: () => void;
}

const DEFAULT_EPOCHS = 6;
const DEFAULT_LEARNING_RATE = 1e-4;

export function FinetunePanel({
  datasets,
  foundations,
  job,
  starting,
  running,
  error,
  onStart,
  onCancel,
}: FinetunePanelProps): JSX.Element {
  const [name, setName] = useState('');
  const [epochs, setEpochs] = useState(DEFAULT_EPOCHS);
  const [selected, setSelected] = useState<readonly string[]>([]);
  const [baseOverride, setBaseOverride] = useState('');

  // Only the *catalogue* detectors can be fine-tuned: an instance is already a fine-tune,
  // and training one again would compound its drift from the COCO weights it started at.
  const bases = foundations.filter(
    (entry) => entry.render_hint === 'boxes' && entry.installed && entry.approx_size_mb > 0,
  );
  // Derived, never seeded from an async fetch — the rule this project keeps relearning.
  const baseId = baseOverride || bases[0]?.id || '';
  const ready = baseId !== '' && selected.length > 0 && name.trim().length > 0;

  if (bases.length === 0) {
    return (
      <p role="status" className="trainer__dim">
        No general detector is installed. Get one in <strong>Admin / Models</strong> —
        RF-DETR is 116 MB and Apache-2.0.
      </p>
    );
  }

  return (
    <div className="finetune">
      <FieldHint id="finetune-hint">
        Starts from a detector that already works and adapts it to your classes. The DINOv2
        backbone stays frozen; only the decoder trains. Expect <strong>minutes</strong>, not
        the seconds a head takes, and about 115 MB per saved model.
      </FieldHint>

      <label className="genpanel__field">
        <span>Name</span>
        <input
          type="text"
          value={name}
          placeholder="Thermal detector"
          disabled={running}
          onChange={(event) => setName(event.target.value)}
        />
      </label>

      <fieldset className="headpick">
        <legend>Start from</legend>
        {bases.map((entry) => (
          <label key={entry.id} className="headpick__option">
            <input
              type="radio"
              name="finetune-base"
              value={entry.id}
              checked={baseId === entry.id}
              disabled={running}
              onChange={() => setBaseOverride(entry.id)}
            />
            <span className="headpick__name">{entry.title}</span>
            <span className="headpick__meta">{entry.description}</span>
          </label>
        ))}
      </fieldset>

      <fieldset className="headpick">
        <legend>Datasets</legend>
        {datasets.length === 0 && (
          <p role="status" className="headpick__empty">
            No datasets yet — annotate some images first.
          </p>
        )}
        {datasets.map((dataset) => (
          <label key={dataset.id} className="headpick__option">
            <input
              type="checkbox"
              checked={selected.includes(dataset.id)}
              disabled={running}
              onChange={() =>
                setSelected((current) =>
                  current.includes(dataset.id)
                    ? current.filter((id) => id !== dataset.id)
                    : [...current, dataset.id],
                )
              }
            />
            <span className="headpick__name">{dataset.name}</span>
            <span className="headpick__meta">{dataset.counts.images} images</span>
          </label>
        ))}
      </fieldset>

      <label className="genpanel__field">
        <span>Epochs — {epochs}</span>
        <input
          type="range"
          min={1}
          max={30}
          value={epochs}
          disabled={running}
          onChange={(event) => setEpochs(Number(event.target.value))}
        />
      </label>

      {error && <p className="run__warn">{error}</p>}

      <div className="finetune__actions">
        <button
          type="button"
          className="btn btn--primary"
          disabled={!ready || starting || running}
          onClick={() =>
            onStart({
              foundationId: baseId,
              datasetIds: [...selected],
              name: name.trim(),
              epochs,
              learningRate: DEFAULT_LEARNING_RATE,
            })
          }
        >
          {starting ? 'Starting…' : 'Fine-tune'}
        </button>
        {running && (
          <button type="button" className="btn" onClick={onCancel}>
            Stop, keep best
          </button>
        )}
      </div>

      {job && <FinetuneProgress job={job} />}
    </div>
  );
}

function FinetuneProgress({ job }: { readonly job: FinetuneJob }): JSX.Element {
  const latest = job.history.at(-1);
  const percent = job.total_epochs > 0 ? (job.epoch / job.total_epochs) * 100 : 0;

  return (
    <div className="finetune__progress">
      <div
        className="progress"
        role="progressbar"
        aria-label={`Epoch ${job.epoch} of ${job.total_epochs}`}
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="progress__bar" style={{ width: `${percent}%` }} />
      </div>

      <p className="finetune__stats">
        {job.state} · epoch {job.epoch}/{job.total_epochs}
        {job.best_metric !== null && <> · best map {job.best_metric.toFixed(3)}</>}
        {latest && <> · loss {latest.train_loss.toFixed(2)}</>}
      </p>

      {job.trainable_parameters > 0 && (
        <p className="finetune__frozen">
          {(job.frozen_parameters / 1e6).toFixed(1)}M frozen ·{' '}
          {(job.trainable_parameters / 1e6).toFixed(1)}M training
          {job.class_names.length > 0 && <> · {job.class_names.join(', ')}</>}
        </p>
      )}

      {job.message && <p className="trainer__dim">{job.message}</p>}
      {job.instance_id && job.state === 'complete' && (
        <p className="finetune__saved">
          Saved. It is now in the detector list in the Annotation Studio, the Dataset
          Generator and the Inference Viewer.
        </p>
      )}
    </div>
  );
}

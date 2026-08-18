/**
 * Training configuration form.
 *
 * Every option shown comes from the backend registries. Incompatible or non-trainable
 * head types are listed with their reason rather than hidden — the user asked for depth
 * to exist, so it must be visible even where it cannot be trained.
 */

import { useMemo, type JSX } from 'react';

import type { BackboneInfo } from '../api/backbones';
import type { DatasetInfo } from '../api/datasets';
import type { HeadTypeInfo } from '../api/heads';

export interface TrainerSelection {
  readonly datasetIds: readonly string[];
  readonly backboneId: string;
  readonly headTypeId: string;
  readonly epochs: number;
  readonly learningRate: number;
  readonly earlyStoppingPatience: number;
}

export interface TrainerFormProps {
  readonly datasets: readonly DatasetInfo[];
  readonly backbones: readonly BackboneInfo[];
  readonly headTypes: readonly HeadTypeInfo[];
  readonly value: TrainerSelection;
  readonly disabled: boolean;
  readonly starting: boolean;
  readonly onChange: (next: TrainerSelection) => void;
  readonly onSubmit: () => void;
}

/** Why the run cannot start, or null when it can. Shown next to the button: a disabled
 *  control with no explanation leaves the user guessing what is missing. */
export function blockingReason(
  value: TrainerSelection,
  headTypes: readonly HeadTypeInfo[],
  backbones: readonly BackboneInfo[],
): string | null {
  if (backbones.length === 0) {
    return 'No backbone installed — download one in Admin / Models first.';
  }
  if (!value.backboneId) return 'Choose a backbone.';
  if (value.datasetIds.length === 0) return 'Choose at least one dataset.';
  if (!value.headTypeId) return 'Choose a head type.';

  const headType = headTypes.find((candidate) => candidate.id === value.headTypeId);
  if (!headType) return 'Choose a head type.';
  if (!headType.trainable) {
    return `${headType.title} cannot be trained here — use its pretrained default for inference.`;
  }
  if (headType.compatible === false) {
    return headType.incompatible_reason ?? 'That head type does not fit this backbone.';
  }
  return null;
}

export function TrainerForm({
  datasets,
  backbones,
  headTypes,
  value,
  disabled,
  starting,
  onChange,
  onSubmit,
}: TrainerFormProps): JSX.Element {
  const blocked = useMemo(
    () => blockingReason(value, headTypes, backbones),
    [value, headTypes, backbones],
  );

  const toggleDataset = (id: string): void => {
    const next = value.datasetIds.includes(id)
      ? value.datasetIds.filter((existing) => existing !== id)
      : [...value.datasetIds, id];
    onChange({ ...value, datasetIds: next });
  };

  return (
    <form
      className="trainer__form"
      onSubmit={(event) => {
        event.preventDefault();
        if (!blocked) onSubmit();
      }}
    >
      <fieldset className="trainer__group" disabled={disabled}>
        <legend>Datasets</legend>
        {datasets.length === 0 ? (
          <p className="trainer__empty">
            No datasets yet — annotate some images in the Annotation Studio first.
          </p>
        ) : (
          <ul className="trainer__checks">
            {datasets.map((dataset) => (
              <li key={dataset.id}>
                <label>
                  <input
                    type="checkbox"
                    checked={value.datasetIds.includes(dataset.id)}
                    onChange={() => toggleDataset(dataset.id)}
                  />
                  <span>
                    {dataset.name}{' '}
                    <span className="trainer__dim">({dataset.counts.images} images)</span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
      </fieldset>

      <fieldset className="trainer__group" disabled={disabled}>
        <legend>Backbone</legend>
        <select
          aria-label="Backbone"
          value={value.backboneId}
          onChange={(event) => onChange({ ...value, backboneId: event.target.value })}
        >
          <option value="">Select a backbone…</option>
          {backbones.map((backbone) => (
            <option key={backbone.id} value={backbone.id}>
              {backbone.id}
              {backbone.capabilities ? ` — ${backbone.capabilities.embed_dim}d` : ''}
            </option>
          ))}
        </select>
      </fieldset>

      <fieldset className="trainer__group" disabled={disabled}>
        <legend>Head type</legend>
        <ul className="trainer__heads">
          {headTypes.map((headType) => {
            const unavailable = !headType.trainable || headType.compatible === false;
            const reason = !headType.trainable
              ? 'Usable for inference via its pretrained default — not trainable here.'
              : headType.incompatible_reason;
            return (
              <li key={headType.id}>
                <label className={unavailable ? 'trainer__head trainer__head--off' : 'trainer__head'}>
                  <input
                    type="radio"
                    name="head-type"
                    value={headType.id}
                    checked={value.headTypeId === headType.id}
                    disabled={unavailable}
                    onChange={() => onChange({ ...value, headTypeId: headType.id })}
                  />
                  <span>
                    <strong>{headType.title}</strong>
                    <span className="trainer__dim"> · {headType.metrics.join(', ')}</span>
                    <br />
                    <span className="trainer__dim">{headType.description}</span>
                    {reason && <em className="trainer__reason">{reason}</em>}
                  </span>
                </label>
              </li>
            );
          })}
        </ul>
      </fieldset>

      <fieldset className="trainer__group trainer__group--inline" disabled={disabled}>
        <legend>Training</legend>
        <label>
          Epochs
          <input
            type="number"
            min={1}
            max={1000}
            value={value.epochs}
            onChange={(event) => onChange({ ...value, epochs: Number(event.target.value) })}
          />
        </label>
        <label>
          Learning rate
          <input
            type="number"
            step="0.0001"
            min={0.0001}
            value={value.learningRate}
            onChange={(event) => onChange({ ...value, learningRate: Number(event.target.value) })}
          />
        </label>
        <label>
          Early stop patience
          <input
            type="number"
            min={1}
            value={value.earlyStoppingPatience}
            onChange={(event) =>
              onChange({ ...value, earlyStoppingPatience: Number(event.target.value) })
            }
          />
        </label>
      </fieldset>

      <div className="trainer__actions">
        <button className="btn" type="submit" disabled={disabled || starting || blocked !== null}>
          {starting ? 'Starting…' : 'Start training'}
        </button>
        {blocked && <span className="trainer__blocked">{blocked}</span>}
      </div>
    </form>
  );
}

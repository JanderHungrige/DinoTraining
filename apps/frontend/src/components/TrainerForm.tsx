/**
 * Training configuration form.
 *
 * Every option shown comes from the backend registries. Incompatible or non-trainable
 * head types are listed with their reason rather than hidden — the user asked for depth
 * to exist, so it must be visible even where it cannot be trained.
 */

import { useMemo, type JSX, type ReactNode } from 'react';

import type { BackboneInfo } from '../api/backbones';
import type { DatasetInfo } from '../api/datasets';
import type { HeadTypeInfo } from '../api/heads';

export interface TrainerSelection {
  readonly datasetIds: readonly string[];
  readonly backboneId: string;
  readonly headTypeId: string;
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
  /** Doc 100: the catalogue's parameter form, in place of hand-written fields. */
  readonly settings?: ReactNode;
  /** Why a setting cannot be sent, e.g. "Rounds: Between 1 and 1000." — or ''. */
  readonly settingsProblem?: string;
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
  settings,
  settingsProblem = '',
}: TrainerFormProps): JSX.Element {
  const blocked = useMemo(
    () => blockingReason(value, headTypes, backbones) ?? (settingsProblem || null),
    [value, headTypes, backbones, settingsProblem],
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

      {settings}

      <div className="trainer__actions">
        <button className="btn" type="submit" disabled={disabled || starting || blocked !== null}>
          {starting ? 'Starting…' : 'Start training'}
        </button>
        {blocked && <span className="trainer__blocked">{blocked}</span>}
      </div>
    </form>
  );
}

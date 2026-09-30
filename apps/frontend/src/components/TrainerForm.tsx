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
import { useT, type Translator } from '../i18n';

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
  { t }: Translator,
): string | null {
  if (backbones.length === 0) return t('training.form.noBackbone');
  if (!value.backboneId) return t('training.form.chooseBackbone');
  if (value.datasetIds.length === 0) return t('training.form.chooseDataset');
  if (!value.headTypeId) return t('training.form.chooseHeadType');

  const headType = headTypes.find((candidate) => candidate.id === value.headTypeId);
  if (!headType) return t('training.form.chooseHeadType');
  if (!headType.trainable) return t('training.form.notTrainable', { title: headType.title });
  if (headType.compatible === false) {
    return headType.incompatible_reason ?? t('training.form.incompatible');
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
  const translator = useT();
  const { t, tp } = translator;
  const blocked = useMemo(
    () => blockingReason(value, headTypes, backbones, translator) ?? (settingsProblem || null),
    [value, headTypes, backbones, settingsProblem, translator],
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
        <legend>{t('training.form.datasets')}</legend>
        {datasets.length === 0 ? (
          <p className="trainer__empty">{t('training.form.noDatasets')}</p>
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
                    <span className="trainer__dim">{tp('training.form.images', dataset.counts.images)}</span>
                  </span>
                </label>
              </li>
            ))}
          </ul>
        )}
      </fieldset>

      <fieldset className="trainer__group" disabled={disabled}>
        <legend>{t('training.form.backbone')}</legend>
        <select
          aria-label={t('training.form.backbone')}
          value={value.backboneId}
          onChange={(event) => onChange({ ...value, backboneId: event.target.value })}
        >
          <option value="">{t('training.form.selectBackbone')}</option>
          {backbones.map((backbone) => (
            <option key={backbone.id} value={backbone.id}>
              {backbone.id}
              {backbone.capabilities ? ` — ${backbone.capabilities.embed_dim}d` : ''}
            </option>
          ))}
        </select>
      </fieldset>

      <fieldset className="trainer__group" disabled={disabled}>
        <legend>{t('training.form.headType')}</legend>
        <ul className="trainer__heads">
          {headTypes.map((headType) => {
            const unavailable = !headType.trainable || headType.compatible === false;
            const reason = !headType.trainable
              ? t('training.form.inferenceOnly')
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
          {starting ? t('training.form.starting') : t('training.form.start')}
        </button>
        {blocked && <span className="trainer__blocked">{blocked}</span>}
      </div>
    </form>
  );
}

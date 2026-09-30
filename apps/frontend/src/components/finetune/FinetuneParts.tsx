/**
 * The fine-tune panel's three read-outs (doc 97): what the model needs, whether the chosen
 * data meets it, and what fine-tuning changed.
 */

import type { JSX } from 'react';

import type { FinetuneJobInfo, FinetuneRequirements, Readiness } from '../../api/finetune';
import { useT, type Key, type Translator } from '../../i18n';

const KIND: Readonly<Record<string, Key>> = {
  boxes: 'training.finetune.kind.boxes',
  'instance-masks': 'training.finetune.kind.instanceMasks',
  'phrase-masks': 'training.finetune.kind.phraseMasks',
  'image-labels': 'training.finetune.kind.imageLabels',
};

/** The side the backend compared on ("test" or "validation"), as a heading. */
const SIDE: Readonly<Record<string, Key>> = {
  test: 'training.finetune.onTest',
  validation: 'training.finetune.onValidation',
};

/** Doc 92's contract, as a person reads it. */
export function RequirementsCard({ spec }: { readonly spec: FinetuneRequirements }): JSX.Element {
  const { t } = useT();
  const needs = t('training.finetune.needs', { model: spec.label });
  const kind = KIND[spec.annotation_kind];
  return (
    <section className="ft-card" aria-label={needs}>
      <h4 className="ft-card__title">{needs}</h4>
      <dl className="ft-card__facts">
        <dt>{t('training.finetune.annotations')}</dt>
        <dd>{kind ? t(kind) : spec.annotation_kind}</dd>
        <dt>{t('training.finetune.atLeast')}</dt>
        <dd>
          {t('training.finetune.minimums', {
            images: spec.min_images,
            perClass: spec.min_instances_per_class,
          })}
        </dd>
        <dt>{t('training.finetune.pictures')}</dt>
        <dd>{spec.image_sizes}</dd>
        <dt>{t('training.finetune.recipe')}</dt>
        <dd>{t(spec.recipe_required ? 'training.finetune.recipeRequired' : 'training.finetune.recipeRecommended')}</dd>
      </dl>
      <p className="ft-card__format">{spec.data_format}</p>
      <p className="ft-card__why">{spec.minimums_why}</p>
      <p className="ft-card__trains">
        <strong>{t('training.finetune.whatTrains')} </strong>
        {spec.what_trains}
      </p>
      {spec.gates.map((gate) => (
        <p key={gate} className="prep-step__note">
          {gate}
        </p>
      ))}
      {!spec.available && <p className="run__warn">{spec.unavailable_reason}</p>}
    </section>
  );
}

/** Doc 92's preflight: every rule, passed or with its fix. */
export function ReadinessList({ readiness }: { readonly readiness: Readiness }): JSX.Element {
  const { t } = useT();
  return (
    <ul className="ft-checks" aria-label={t('training.finetune.ready')}>
      {readiness.checks.map((check) => (
        <li key={check.id} className={check.passed ? 'ft-checks__ok' : 'ft-checks__fail'}>
          <span aria-hidden="true">{check.passed ? '✓' : '✗'}</span> <strong>{check.title}</strong> —{' '}
          {check.detail}
          {!check.passed && check.fix && <span className="ft-checks__fix"> {check.fix}</span>}
        </li>
      ))}
    </ul>
  );
}

function heldOutHeading(side: string, t: Translator['t']): string {
  if (!side) return t('training.finetune.onHeldOut');
  const known = SIDE[side];
  return known ? t(known) : t('training.finetune.onPictures', { heldOut: side });
}

function score(metrics: Readonly<Record<string, number>>, key: string): string {
  const value = metrics[key];
  return value === undefined ? '—' : value.toFixed(3);
}

/** Doc 93: the base and the fine-tuned model on the same held-out pictures. */
export function FinetuneResult({ job }: { readonly job: FinetuneJobInfo }): JSX.Element {
  const { t } = useT();
  const key = job.primary_metric;
  return (
    <section className="ft-result" aria-label={t('training.finetune.beforeAfter')}>
      <table className="prep-table">
        <thead>
          <tr>
            <th>{heldOutHeading(job.held_out, t)}</th>
            <th>{key}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">{t('training.finetune.before')}</th>
            <td>{score(job.baseline_metrics, key)}</td>
          </tr>
          <tr>
            <th scope="row">
              {job.best_epoch
                ? t('training.finetune.afterRound', { round: job.best_epoch })
                : t('training.finetune.after')}
            </th>
            <td>{score(job.final_metrics, key)}</td>
          </tr>
        </tbody>
      </table>
      {job.notes.map((note) => (
        <p key={note} className="prep-step__note">
          {note}
        </p>
      ))}
      {job.instance_id && (
        <p className="trainer__hint">{t('training.finetune.saved')}</p>
      )}
    </section>
  );
}

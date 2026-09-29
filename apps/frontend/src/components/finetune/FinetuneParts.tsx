/**
 * The fine-tune panel's three read-outs (doc 97): what the model needs, whether the chosen
 * data meets it, and what fine-tuning changed.
 */

import type { JSX } from 'react';

import type { FinetuneJobInfo, FinetuneRequirements, Readiness } from '../../api/finetune';

const KIND: Readonly<Record<string, string>> = {
  boxes: 'Boxes',
  'instance-masks': 'Outlines (one mask per object)',
  'phrase-masks': 'Outlines named by a phrase',
  'image-labels': 'One class per image',
};

/** Doc 92's contract, as a person reads it. */
export function RequirementsCard({ spec }: { readonly spec: FinetuneRequirements }): JSX.Element {
  return (
    <section className="ft-card" aria-label={`What ${spec.label} needs`}>
      <h4 className="ft-card__title">What {spec.label} needs</h4>
      <dl className="ft-card__facts">
        <dt>Annotations</dt>
        <dd>{KIND[spec.annotation_kind] ?? spec.annotation_kind}</dd>
        <dt>At least</dt>
        <dd>
          {spec.min_images} images, {spec.min_instances_per_class} per class
        </dd>
        <dt>Pictures</dt>
        <dd>{spec.image_sizes}</dd>
        <dt>Recipe</dt>
        <dd>{spec.recipe_required ? 'Required (Prepare data)' : 'Recommended'}</dd>
      </dl>
      <p className="ft-card__format">{spec.data_format}</p>
      <p className="ft-card__why">{spec.minimums_why}</p>
      <p className="ft-card__trains">
        <strong>What trains: </strong>
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
  return (
    <ul className="ft-checks" aria-label="Is the data ready?">
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

function score(metrics: Readonly<Record<string, number>>, key: string): string {
  const value = metrics[key];
  return value === undefined ? '—' : value.toFixed(3);
}

/** Doc 93: the base and the fine-tuned model on the same held-out pictures. */
export function FinetuneResult({ job }: { readonly job: FinetuneJobInfo }): JSX.Element {
  const key = job.primary_metric;
  return (
    <section className="ft-result" aria-label="Before and after">
      <table className="prep-table">
        <thead>
          <tr>
            <th>On the {job.held_out || 'held-out'} pictures</th>
            <th>{key}</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Before (base)</th>
            <td>{score(job.baseline_metrics, key)}</td>
          </tr>
          <tr>
            <th scope="row">After fine-tuning{job.best_epoch ? ` (round ${job.best_epoch})` : ''}</th>
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
        <p className="trainer__hint">Saved. It is now offered wherever its kind of model is: pick it by name.</p>
      )}
    </section>
  );
}

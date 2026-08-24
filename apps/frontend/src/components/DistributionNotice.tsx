/**
 * What you must deal with before shipping this app (doc 54).
 *
 * Wave 8 is packaging, and the constraint is not a property of the *catalogue* — it is a
 * property of **what the user has actually downloaded**. So this lists installed models
 * only, and disappears entirely when there is nothing to say.
 *
 * It lives in Admin because that is where the fix is: the remove button is a few
 * centimetres below. A notice in the Library would name a problem and point elsewhere.
 *
 * **It does not say "non-commercial" about everything**, and that is the point. Three
 * different obligations get three different sentences, because collapsing them is how
 * someone concludes an AGPL model cannot be sold — when in fact it can, and the real
 * obligation is that shipping it makes the whole app AGPL, which is a far bigger decision
 * than deleting a file.
 */

import type { JSX } from 'react';

import type { ModelInfo } from '../api/models';

export interface DistributionNoticeProps {
  readonly models: readonly ModelInfo[];
}

/** Installed models whose licence obliges something at distribution time. */
export function restrictedInstalled(models: readonly ModelInfo[]): ModelInfo[] {
  return models.filter((model) => model.installed && model.redistribution !== 'free');
}

export function DistributionNotice({ models }: DistributionNoticeProps): JSX.Element | null {
  const restricted = restrictedInstalled(models);
  if (restricted.length === 0) return null;

  return (
    <section className="distnotice" aria-labelledby="distnotice-title">
      <h3 className="distnotice__title" id="distnotice-title">
        <span aria-hidden="true">⚠</span> Before you distribute this app
      </h3>
      <p className="distnotice__lead">
        {restricted.length} installed model{restricted.length === 1 ? '' : 's'} come
        {restricted.length === 1 ? 's' : ''} with a licence obligation. Everything else you
        have installed is permissively licensed and can ship as-is.
      </p>

      <ul className="distnotice__list">
        {restricted.map((model) => (
          <li key={model.id} className="distnotice__row">
            <span className="distnotice__name">{model.repo_id}</span>
            <span className={`badge badge--${model.redistribution}`}>{model.licence}</span>
            <span className="distnotice__note">{model.redistribution_note}</span>
          </li>
        ))}
      </ul>

      <p className="distnotice__foot">
        Removing a model here deletes its weights from the cache, which is what takes it out
        of a build — nothing else has to change. You can download it again afterwards.
      </p>
    </section>
  );
}

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
import { useT } from '../i18n';

export interface DistributionNoticeProps {
  readonly models: readonly ModelInfo[];
}

/** Installed models whose licence obliges something at distribution time. */
export function restrictedInstalled(models: readonly ModelInfo[]): ModelInfo[] {
  return models.filter((model) => model.installed && model.redistribution !== 'free');
}

export function DistributionNotice({ models }: DistributionNoticeProps): JSX.Element | null {
  const { t, tp } = useT();
  const restricted = restrictedInstalled(models);
  if (restricted.length === 0) return null;

  return (
    <section className="distnotice" aria-labelledby="distnotice-title">
      <h3 className="distnotice__title" id="distnotice-title">
        <span aria-hidden="true">⚠</span> {t('admin.dist.title')}
      </h3>
      <p className="distnotice__lead">{tp('admin.dist.lead', restricted.length)}</p>

      <ul className="distnotice__list">
        {restricted.map((model) => (
          <li key={model.id} className="distnotice__row">
            <span className="distnotice__name">{model.repo_id}</span>
            <span className={`badge badge--${model.redistribution}`}>{model.licence}</span>
            <span className="distnotice__note">{model.redistribution_note}</span>
          </li>
        ))}
      </ul>

      <p className="distnotice__foot">{t('admin.dist.foot')}</p>
    </section>
  );
}

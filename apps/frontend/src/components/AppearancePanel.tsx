/**
 * Admin › Appearance (doc 77): the one look setting a user may want to change.
 */

import type { JSX } from 'react';

import { useT } from '../i18n';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { useLook } from '../lib/look';

export function AppearancePanel(): JSX.Element {
  const { t } = useT();
  const { animatedBackground, setAnimatedBackground } = useLook();
  const reduced = useReducedMotion();

  return (
    <section className="admin__group appearance">
      <h3 className="admin__grouptitle">{t('app.appearance.title')}</h3>
      <label className="appearance__toggle">
        <input
          type="checkbox"
          checked={animatedBackground}
          onChange={(event) => setAnimatedBackground(event.target.checked)}
        />
        {t('app.appearance.animated')}
      </label>
      {reduced && (
        <p className="appearance__hint">
          {t('app.appearance.reduced')}
        </p>
      )}
    </section>
  );
}

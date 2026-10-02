/**
 * Settings › Appearance (docs 77, 164): the colour scheme and the moving background.
 */

import type { JSX } from 'react';

import { useT, type Key } from '../i18n';
import { useReducedMotion } from '../hooks/useReducedMotion';
import { THEMES, useLook, type Theme } from '../lib/look';

const THEME_LABEL: Readonly<Record<Theme, Key>> = {
  system: 'app.appearance.theme.system',
  dark: 'app.appearance.theme.dark',
  light: 'app.appearance.theme.light',
};

export function AppearancePanel(): JSX.Element {
  const { t } = useT();
  const { animatedBackground, setAnimatedBackground, theme, setTheme } = useLook();
  const reduced = useReducedMotion();

  return (
    <section className="admin__group appearance" aria-labelledby="appearance-title">
      <h3 className="admin__grouptitle" id="appearance-title">{t('app.appearance.title')}</h3>
      <fieldset className="appearance__themes">
        <legend>{t('app.appearance.theme')}</legend>
        {THEMES.map((option) => (
          <label key={option} className="appearance__toggle">
            <input
              type="radio"
              name="appearance-theme"
              value={option}
              checked={theme === option}
              onChange={() => setTheme(option)}
            />
            {t(THEME_LABEL[option])}
          </label>
        ))}
      </fieldset>
      <label className="appearance__toggle">
        <input
          type="checkbox"
          checked={animatedBackground}
          onChange={(event) => setAnimatedBackground(event.target.checked)}
        />
        {t('app.appearance.animated')}
      </label>
      {reduced && <p className="appearance__hint">{t('app.appearance.reduced')}</p>}
    </section>
  );
}

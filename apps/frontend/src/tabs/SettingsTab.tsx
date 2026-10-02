/**
 * Settings (doc 164): how the app looks, and where its background comes from.
 *
 * Jan (2026-10-02): "a settings tab with dark / light mode, animation on/off (that is
 * somewhere else right now), the Pexels credit". The appearance switch moved here from
 * Models & Datasets › Official models. The language stays in the top bar, where it can be
 * changed from every tab.
 */

import type { JSX } from 'react';

import { AppearancePanel } from '../components/AppearancePanel';
import { useT } from '../i18n';

export const BACKGROUND_SOURCE = 'https://www.pexels.com/video/trees-in-the-forest-5121476/';

export function SettingsTab(): JSX.Element {
  const { t } = useT();
  return (
    <section className="settings">
      <h2 className="admin__title">{t('settings.title')}</h2>
      <p className="settings__lead">{t('settings.lead')}</p>
      <AppearancePanel />
      <section className="admin__group settings__credits" aria-labelledby="settings-credits">
        <h3 className="admin__grouptitle" id="settings-credits">{t('settings.credits.title')}</h3>
        <p>
          {t('settings.credits.background')}{' '}
          <a href={BACKGROUND_SOURCE} target="_blank" rel="noreferrer noopener">
            {t('settings.credits.link')}
          </a>
        </p>
      </section>
    </section>
  );
}

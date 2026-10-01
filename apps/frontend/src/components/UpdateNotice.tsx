/**
 * "DinoTraining 0.1.3 is available" (doc 158).
 *
 * The shell asks once at start (`check_for_update`) and answers only for the installer
 * edition: the Store updates its own, a dev build is whatever is checked out. "Later" is
 * remembered for that version, so the bar returns only when a newer one comes out.
 */

import { useEffect, useState, type JSX } from 'react';

import { useT } from '../i18n';
import { isString, readPersisted, writePersisted } from '../lib/persisted';
import { inShell } from '../setup/shell';

const DISMISSED = 'update.dismissedVersion';

export interface Update {
  readonly current: string;
  readonly latest: string;
  readonly notes: string;
  readonly download: string;
}

export function UpdateNotice(): JSX.Element | null {
  const { t } = useT();
  const [update, setUpdate] = useState<Update | null>(null);

  useEffect(() => {
    if (!inShell()) return;
    let cancelled = false;
    void import('@tauri-apps/api/core')
      .then(({ invoke }) => invoke<Update | null>('check_for_update'))
      .then((answer) => {
        if (cancelled || !answer) return;
        if (readPersisted(DISMISSED, '', isString) === answer.latest) return;
        setUpdate(answer);
      })
      // The shell logs why; a failed check never gets in the way.
      .catch((error: unknown) => console.warn('check_for_update failed', error));
    return () => {
      cancelled = true;
    };
  }, []);

  if (!update) return null;

  const later = (): void => {
    writePersisted(DISMISSED, update.latest);
    setUpdate(null);
  };

  return (
    <div className="addapps updatenotice" role="status">
      <span>{t('app.update.available', { latest: update.latest, current: update.current })}</span>
      <a className="btn btn--primary btn--small" href={update.download} target="_blank" rel="noreferrer">
        {t('app.update.get')}
      </a>
      <a className="btn btn--small" href={update.notes} target="_blank" rel="noreferrer">
        {t('app.update.notes')}
      </a>
      <button type="button" className="btn btn--small" onClick={later}>
        {t('app.update.later')}
      </button>
    </div>
  );
}

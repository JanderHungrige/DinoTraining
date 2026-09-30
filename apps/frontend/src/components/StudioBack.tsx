/**
 * Back to the Studio's overview. The session is kept while other tabs are visited (App keeps
 * the Studio mounted), so this is the one way to end it — and it asks first when the picture
 * has unsaved changes, rather than dropping them.
 */

import { useState, type JSX } from 'react';

import { useT } from '../i18n';

export interface StudioBackProps {
  readonly dirty: boolean;
  readonly busy: boolean;
  /** False when the save failed: then the session stays, with its error shown. */
  readonly onSave: () => Promise<boolean>;
  readonly onBack: () => void;
}

export function StudioBack({ dirty, busy, onSave, onBack }: StudioBackProps): JSX.Element {
  const { t } = useT();
  const [asking, setAsking] = useState(false);

  const saveAndGo = async (): Promise<void> => {
    if (await onSave()) onBack();
    else setAsking(false);
  };

  return (
    <div className="studio__back">
      <button
        type="button"
        className="btn"
        title={t('studio.back.hint')}
        disabled={busy}
        onClick={() => (dirty ? setAsking(true) : onBack())}
      >
        {t('studio.back.button')}
      </button>
      {asking && dirty && (
        <div className="studio__backask" role="alertdialog" aria-label={t('studio.back.unsaved')}>
          <p className="run__warn">{t('studio.back.unsaved')}</p>
          <button type="button" className="btn btn--primary" disabled={busy} onClick={() => void saveAndGo()}>
            {t('studio.back.saveAndGo')}
          </button>
          <button type="button" className="btn" onClick={onBack}>
            {t('studio.back.discard')}
          </button>
          <button type="button" className="btn" onClick={() => setAsking(false)}>
            {t('studio.back.stay')}
          </button>
        </div>
      )}
    </div>
  );
}

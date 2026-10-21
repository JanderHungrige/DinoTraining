/**
 * Settings › Feedback (doc 171): report an issue or suggest an idea, without an error.
 *
 * The desktop app uses doc 140's `report_issue` with no message, so the issue still
 * carries the version, the OS and the log's last lines. Outside it, a plain link to
 * GitHub's new-issue page. Never posted from the app: the user submits it themselves.
 */

import { useState, type JSX } from 'react';

import { useT } from '../i18n';
import { inShell } from '../setup/shell';

export const NEW_ISSUE = 'https://github.com/JanderHungrige/DinoTraining/issues/new';

export function ReportIssuePanel(): JSX.Element {
  const { t } = useT();
  const [note, setNote] = useState<string | null>(null);
  const report = (): void => {
    setNote(null);
    void import('@tauri-apps/api/core')
      .then(({ invoke }) => invoke<void>('report_issue', { message: '' }))
      .catch((error: unknown) => setNote(t('app.report.failed', { reason: String(error) })));
  };
  return (
    <section className="admin__group" aria-labelledby="settings-feedback">
      <h3 className="admin__grouptitle" id="settings-feedback">{t('settings.feedback.title')}</h3>
      <p>{t('settings.feedback.lead')}</p>
      {inShell() ? (
        <button type="button" className="btn btn--small" onClick={report}>
          {t('settings.feedback.report')}
        </button>
      ) : (
        <a className="btn btn--small" href={NEW_ISSUE} target="_blank" rel="noreferrer noopener">
          {t('settings.feedback.report')}
        </a>
      )}
      {note && <p className="erroractions__note">{note}</p>}
    </section>
  );
}

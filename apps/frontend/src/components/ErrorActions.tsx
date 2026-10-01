/**
 * "Open the log" and "Report an issue" beside an error (doc 140).
 *
 * Only in the desktop app: the log lives on this machine, and the shell opens it with
 * the system's default program. The report opens a prefilled GitHub issue in the
 * browser; the user reviews it and submits it with their own account.
 */

import { useState, type JSX } from 'react';

import { useT } from '../i18n';
import { inShell } from '../setup/shell';

async function invoke<T>(command: string, args?: Record<string, unknown>): Promise<T> {
  const { invoke: call } = await import('@tauri-apps/api/core');
  return call<T>(command, args);
}

export function ErrorActions({ message }: { readonly message: string }): JSX.Element | null {
  const { t } = useT();
  const [note, setNote] = useState<string | null>(null);
  if (!inShell()) return null;

  const openLog = (): void => {
    setNote(null);
    invoke<string>('open_backend_log').catch((error: unknown) => setNote(String(error)));
  };
  const report = (): void => {
    setNote(null);
    invoke<void>('report_issue', { message }).catch((error: unknown) =>
      setNote(t('app.report.failed', { reason: String(error) })),
    );
  };

  return (
    <div className="erroractions">
      <button type="button" className="btn btn--small" onClick={openLog}>
        {t('app.report.openLog')}
      </button>
      <button type="button" className="btn btn--small" onClick={report} title={t('app.report.issueHint')}>
        {t('app.report.issue')}
      </button>
      {note && <p className="erroractions__note">{note}</p>}
    </div>
  );
}

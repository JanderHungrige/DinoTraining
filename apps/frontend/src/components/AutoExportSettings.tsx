/**
 * "Automatic export" above the Datasets list (doc 144): on closing, every n minutes,
 * "Export all now", and what the last run did — including which datasets have no target.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import {
  getExportSettings,
  getExportStatus,
  putExportSettings,
  runExports,
  SETTINGS_EVENT,
  type AutoReport,
  type ExportSettings,
} from '../api/exports';
import { useT } from '../i18n';
import { since } from './DatasetExport';

const DEFAULT_MINUTES = 10;

function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

const names = (entries: readonly { readonly name: string }[]): string => entries.map((entry) => entry.name).join(', ');

export function AutoExportSettings({ onExported }: { readonly onExported: () => void }): JSX.Element | null {
  const { t } = useT();
  const [settings, setSettings] = useState<ExportSettings | null>(null);
  const [report, setReport] = useState<AutoReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState('');

  const readStatus = useCallback((signal?: AbortSignal) => {
    getExportStatus(signal)
      .then((status) => setReport(status.last))
      .catch((error: unknown) => {
        if (!signal?.aborted) setProblem(message(error));
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getExportSettings(controller.signal)
      .then(setSettings)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setProblem(message(error));
      });
    readStatus(controller.signal);
    return () => controller.abort();
  }, [readStatus]);

  if (!settings) return problem ? <p className="dsimport__error" role="alert">{problem}</p> : null;

  const save = (next: ExportSettings): void => {
    setSettings(next);
    putExportSettings(next)
      .then((saved) => {
        setSettings(saved);
        window.dispatchEvent(new Event(SETTINGS_EVENT));
      })
      .catch((error: unknown) => setProblem(message(error)));
  };

  const exportAll = async (): Promise<void> => {
    setBusy(true);
    setProblem('');
    try {
      const answer = await runExports('manual', true);
      if (answer.report) setReport(answer.report);
      onExported();
    } catch (error) {
      setProblem(message(error));
    } finally {
      setBusy(false);
    }
  };

  const every = settings.every_minutes > 0;
  return (
    <section className="dsimport autoexport" aria-labelledby="autoexport-title">
      <h3 id="autoexport-title" className="dsimport__title">{t('models.auto.title')}</h3>
      <p className="dsimport__lead">{t('models.auto.lead')}</p>
      <div className="autoexport__row">
        <label className="dsimport__check">
          <input type="checkbox" checked={settings.on_close} onChange={(event) => save({ ...settings, on_close: event.target.checked })} />
          {t('models.auto.onClose')}
        </label>
        <label className="dsimport__check">
          <input
            type="checkbox"
            checked={every}
            onChange={(event) => save({ ...settings, every_minutes: event.target.checked ? DEFAULT_MINUTES : 0 })}
          />
          {t('models.auto.every')}
        </label>
        <input
          type="number"
          className="autoexport__minutes"
          min={1}
          max={1440}
          disabled={!every}
          aria-label={t('models.auto.minutes')}
          value={every ? settings.every_minutes : DEFAULT_MINUTES}
          onChange={(event) => {
            const minutes = Math.round(Number(event.target.value));
            if (minutes >= 1 && minutes <= 1440) save({ ...settings, every_minutes: minutes });
          }}
        />
        <span>{t('models.auto.minutes')}</span>
        <button type="button" className="btn btn--small" disabled={busy} onClick={() => void exportAll()}>
          {busy ? t('models.auto.busy') : t('models.auto.now')}
        </button>
      </div>
      {report && <LastRun report={report} />}
      {problem && <p className="dsimport__error" role="alert">{problem}</p>}
    </section>
  );
}

function LastRun({ report }: { readonly report: AutoReport }): JSX.Element {
  const { t, lang } = useT();
  return (
    <div className="autoexport__last" role="status">
      <p>
        {t('models.auto.last', {
          when: since(report.finished_at ?? report.started_at, lang),
          exported: String(report.exported.length),
          unchanged: String(report.unchanged),
        })}
      </p>
      {report.failed.length > 0 && (
        <p className="run__warn">
          {t('models.auto.failed', { names: names(report.failed) })}{' '}
          {report.failed.map((entry) => entry.error).join(' · ')}
        </p>
      )}
      {report.unfinished.length > 0 && <p className="run__warn">{t('models.auto.unfinished', { names: names(report.unfinished) })}</p>}
      {report.no_target.length > 0 && <p className="dsimport__note">{t('models.auto.noTarget', { names: names(report.no_target) })}</p>}
    </div>
  );
}

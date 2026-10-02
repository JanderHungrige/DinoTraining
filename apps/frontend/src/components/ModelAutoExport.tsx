/**
 * "Export trained models automatically" above My Models (doc 145): each trained model is
 * exported to this folder when its training finishes. Off unless a folder is chosen.
 */

import { useEffect, useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import { getExportSettings, putExportSettings, type ExportSettings } from '../api/exports';
import { useT } from '../i18n';
import { hasNativeDialog, pickFolder } from '../lib/dialog';
import { readPersisted, writePersisted } from '../lib/persisted';
import { MODEL_LAST_FOLDER } from './ModelExportActions';

const isString = (value: unknown): value is string => typeof value === 'string';

function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

export function ModelAutoExport(): JSX.Element | null {
  const { t } = useT();
  const [settings, setSettings] = useState<ExportSettings | null>(null);
  // Typed but not yet saved; the saved folder comes from the settings (CLAUDE.md).
  const [draft, setDraft] = useState<string | null>(null);
  const [problem, setProblem] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    getExportSettings(controller.signal)
      .then(setSettings)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setProblem(message(error));
      });
    return () => controller.abort();
  }, []);

  if (!settings) return problem ? <p className="dsimport__error" role="alert">{problem}</p> : null;

  const saved = settings.model_folder ?? null;
  const folder = draft ?? saved ?? readPersisted(MODEL_LAST_FOLDER, '', isString);
  const save = (next: string | null): void => {
    setProblem('');
    putExportSettings({ ...settings, model_folder: next })
      .then((stored) => {
        setSettings(stored);
        setDraft(null);
        if (next) writePersisted(MODEL_LAST_FOLDER, next);
      })
      .catch((error: unknown) => setProblem(message(error)));
  };
  const choose = async (): Promise<void> => {
    const picked = await pickFolder(folder || undefined);
    if (picked) save(picked);
  };

  return (
    <section className="dsimport autoexport" aria-labelledby="modelexport-title">
      <h3 id="modelexport-title" className="dsimport__title">{t('models.modelAuto.title')}</h3>
      <div className="autoexport__row">
        <label className="dsimport__check">
          <input type="checkbox" checked={saved !== null} disabled={saved === null && !folder.trim()}
            onChange={(event) => save(event.target.checked ? folder.trim() : null)} />
          {t('models.modelAuto.on')}
        </label>
        <input type="text" className="autoexport__folder" aria-label={t('models.modelAuto.folder')} placeholder={t('models.modelAuto.folder')}
          value={folder} onChange={(event) => setDraft(event.target.value)}
          onBlur={() => { if (saved !== null && draft !== null && draft.trim() && draft.trim() !== saved) save(draft.trim()); }} />
        {hasNativeDialog() && (
          <button type="button" className="btn btn--small" onClick={() => void choose()}>{t('models.export.choose')}</button>
        )}
      </div>
      {problem && <p className="dsimport__error" role="alert">{problem}</p>}
    </section>
  );
}

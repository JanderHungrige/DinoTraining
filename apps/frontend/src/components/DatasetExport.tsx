/**
 * "Export…" on a dataset row (doc 143): with the data, or to a folder (the dialog opens at
 * the last one used), the pictures copied or not, and when it last went.
 */

import { useEffect, useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import { exportDataset, getExportTarget, setExportTarget, type ExportTarget, type TargetKind } from '../api/datasetExport';
import { useT, type Language } from '../i18n';
import { hasNativeDialog, pickFolder } from '../lib/dialog';
import { readPersisted, writePersisted } from '../lib/persisted';

/** Remembered across datasets: where the user last exported to. */
export const LAST_FOLDER = 'datasets.export.lastFolder';
const isString = (value: unknown): value is string => typeof value === 'string';

const UNITS: readonly [Intl.RelativeTimeFormatUnit, number][] = [
  ['day', 86_400],
  ['hour', 3_600],
  ['minute', 60],
];

/** "3 minutes ago", "yesterday", in the reader's language. */
export function since(at: string, lang: Language, now: number = Date.now()): string {
  const seconds = Math.round((new Date(at).getTime() - now) / 1000);
  const format = new Intl.RelativeTimeFormat(lang, { numeric: 'auto' });
  const [unit, size] = UNITS.find(([, length]) => Math.abs(seconds) >= length) ?? ['second', 1];
  return format.format(Math.round(seconds / size), unit);
}

function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

export interface DatasetExportProps {
  readonly datasetId: string;
  readonly name: string;
  readonly exportedAt: string | null;
  readonly onExported: () => void;
}

export function DatasetExport({ datasetId, name, exportedAt, onExported }: DatasetExportProps): JSX.Element {
  const { t, lang } = useT();
  const [open, setOpen] = useState(false);
  return (
    <span className="library__actions dsexport">
      <span className="library__meta">{exportedAt ? t('models.export.when', { when: since(exportedAt, lang) }) : t('models.export.never')}</span>
      <button type="button" className="btn btn--small" aria-expanded={open} aria-label={t('models.export.label', { name })} onClick={() => setOpen(!open)}>
        {open ? t('models.export.close') : t('models.export.open')}
      </button>
      {open && <ExportPanel datasetId={datasetId} onExported={onExported} />}
    </span>
  );
}

function ExportPanel({ datasetId, onExported }: { readonly datasetId: string; readonly onExported: () => void }): JSX.Element {
  const { t, tp } = useT();
  const [target, setTarget] = useState<ExportTarget | null>(null);
  // Only the user's choices are state; the defaults come from the loaded target (CLAUDE.md).
  const [kindChoice, setKindChoice] = useState<TargetKind | null>(null);
  const [folderChoice, setFolderChoice] = useState<string | null>(null);
  const [picturesChoice, setPicturesChoice] = useState<boolean | null>(null);
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState('');
  const [problem, setProblem] = useState('');

  useEffect(() => {
    const controller = new AbortController();
    getExportTarget(datasetId, controller.signal)
      .then(setTarget)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setProblem(message(error));
      });
    return () => controller.abort();
  }, [datasetId]);

  const offered = target?.data_folder ?? null;
  const kind: TargetKind = kindChoice ?? target?.kind ?? (offered ? 'data' : 'folder');
  const folder = folderChoice ?? target?.folder ?? readPersisted(LAST_FOLDER, '', isString);
  const pictures = picturesChoice ?? target?.include_pictures ?? false;
  const ready = target !== null && !busy && (kind === 'data' ? offered !== null : folder.trim() !== '');

  const choose = async (): Promise<void> => {
    const picked = await pickFolder(folder || undefined);
    if (picked) {
      setFolderChoice(picked);
      setKindChoice('folder');
    }
  };

  const exportNow = async (): Promise<void> => {
    setBusy(true);
    setProblem('');
    setSaid('');
    try {
      await setExportTarget(datasetId, { kind, folder: kind === 'folder' ? folder.trim() : null, include_pictures: pictures });
      const result = await exportDataset(datasetId);
      if (kind === 'folder') writePersisted(LAST_FOLDER, folder.trim());
      setSaid(`${t('models.export.done', { folder: result.folder })} ${tp('models.import.pictures', result.pictures)} · ${tp('models.import.objects', result.objects)}`);
      onExported();
    } catch (error) {
      setProblem(message(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="dsexport__panel" role="group" aria-label={t('models.export.open')}>
      {offered ? (
        <label className="dsexport__choice">
          <input type="radio" name={`target-${datasetId}`} checked={kind === 'data'} onChange={() => setKindChoice('data')} />
          {t('models.export.withData', { folder: offered })}
        </label>
      ) : (
        target && <p className="dsexport__hint">{t('models.export.insideApp')}</p>
      )}
      <div className="dsexport__choice">
        {offered && <input type="radio" name={`target-${datasetId}`} aria-label={t('models.export.toFolder')} checked={kind === 'folder'} onChange={() => setKindChoice('folder')} />}
        <input type="text" aria-label={t('models.export.toFolder')} placeholder={t('models.export.toFolder')} value={folder} onChange={(event) => { setFolderChoice(event.target.value); setKindChoice('folder'); }} />
        {hasNativeDialog() && (
          <button type="button" className="btn btn--small" onClick={() => void choose()}>
            {t('models.export.choose')}
          </button>
        )}
      </div>
      {!(target?.linked && kind === 'data') && (
        <label className="dsexport__choice">
          <input type="checkbox" checked={pictures} onChange={(event) => setPicturesChoice(event.target.checked)} />
          {t('models.export.pictures')}
        </label>
      )}
      <button type="button" className="btn btn--primary btn--small" disabled={!ready} onClick={() => void exportNow()}>
        {busy ? t('models.export.busy') : t('models.export.now')}
      </button>
      {said && <p className="dsexport__done" role="status">{said}</p>}
      {problem && <p className="dsimport__error" role="alert">{problem}</p>}
    </div>
  );
}

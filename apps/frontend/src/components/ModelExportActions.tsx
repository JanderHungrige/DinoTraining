/**
 * "Export" and "Show where it is" for one trained model (doc 121).
 *
 * Export in the desktop app asks for a folder and writes `<name>.zip` there; in a browser
 * the zip downloads. "Show where it is" opens the folder that holds the model — desktop
 * only, since a browser cannot open a local folder.
 */

import { useState, type JSX } from 'react';

import { downloadModelExport, exportModelTo, modelLocation, type ExportKind } from '../api/modelExports';
import { useT } from '../i18n';
import { hasNativeDialog, pickFolder, revealFolder } from '../lib/dialog';

export interface ModelExportActionsProps {
  readonly kind: ExportKind;
  readonly instanceId: string;
  readonly name: string;
}

function saveBlob(name: string, blob: Blob): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = name;
  link.click();
  URL.revokeObjectURL(url);
}

export function ModelExportActions({ kind, instanceId, name }: ModelExportActionsProps): JSX.Element {
  const { t } = useT();
  const [busy, setBusy] = useState(false);
  const [said, setSaid] = useState('');
  const [problem, setProblem] = useState('');
  const desktop = hasNativeDialog();

  const run = async (work: () => Promise<string>): Promise<void> => {
    setBusy(true);
    setProblem('');
    try {
      setSaid(await work());
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  };

  const exportIt = (): Promise<void> =>
    run(async () => {
      if (!desktop) {
        const { name: file, blob } = await downloadModelExport(kind, instanceId);
        saveBlob(file, blob);
        return t('admin.export.downloaded', { file });
      }
      const folder = await pickFolder();
      if (!folder) return '';
      const { path } = await exportModelTo(kind, instanceId, folder);
      return t('admin.export.written', { path });
    });

  const showIt = (): Promise<void> =>
    run(async () => {
      const { folder } = await modelLocation(kind, instanceId);
      await revealFolder(folder);
      return '';
    });

  return (
    <span className="library__actions">
      <button type="button" className="btn btn--small" disabled={busy} title={t('admin.export.hint')} aria-label={t('admin.export.exportNamed', { name })} onClick={() => void exportIt()}>
        {busy ? t('admin.export.busy') : t('admin.export.export')}
      </button>
      {desktop && (
        <button type="button" className="btn btn--small" disabled={busy} aria-label={t('admin.export.showNamed', { name })} onClick={() => void showIt()}>
          {t('admin.export.show')}
        </button>
      )}
      {said && <span className="library__meta" role="status">{said}</span>}
      {problem && <span className="run__warn" role="alert">{problem}</span>}
    </span>
  );
}

/**
 * Doc 146: uninstalling removes everything inside the app; exports stay. Said where the
 * work is, with what is not exported yet and a way to export it now. Under MSIX (Wave
 * 15.10) Windows uninstalls without a page of ours, so this is the only warning there.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { getExportOverview, runExports, type ExportOverview } from '../api/exports';
import { useT } from '../i18n';
import { useEdition } from '../lib/edition';

export function UninstallNotice({ onExported }: { readonly onExported?: () => void }): JSX.Element | null {
  const { t, tp } = useT();
  const [overview, setOverview] = useState<ExportOverview | null>(null);
  const [busy, setBusy] = useState(false);
  // Doc 156: the Store's uninstall has no page of ours and no box to tick.
  const store = useEdition() === 'store';

  const read = useCallback((signal?: AbortSignal) => {
    getExportOverview(signal)
      .then(setOverview)
      // The notice is a courtesy; without its numbers it still says the important part.
      .catch((error: unknown) => {
        if (!signal?.aborted) console.warn('Export overview unavailable', error);
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    read(controller.signal);
    return () => controller.abort();
  }, [read]);

  const exportAll = async (): Promise<void> => {
    setBusy(true);
    try {
      await runExports('manual', true);
      onExported?.();
    } catch (error) {
      console.warn('Export all failed', error);
    } finally {
      setBusy(false);
      read();
    }
  };

  const pending = overview ? overview.no_target.length + overview.unexported.length : 0;
  return (
    <aside className={`uninstall ${pending ? 'uninstall--pending' : ''}`} aria-labelledby="uninstall-title">
      <p id="uninstall-title" className="uninstall__lead">{t(store ? 'models.uninstall.leadStore' : 'models.uninstall.lead')}</p>
      {overview && (
        <p className="uninstall__state">
          {pending === 0 && overview.datasets > 0 && <span>{t('models.uninstall.allExported')} </span>}
          {overview.no_target.length > 0 && <span>{tp('models.uninstall.noTarget', overview.no_target.length, { names: overview.no_target.join(', ') })} </span>}
          {overview.unexported.length > 0 && <span>{tp('models.uninstall.unexported', overview.unexported.length, { names: overview.unexported.join(', ') })} </span>}
          {overview.models > 0 && (
            <span>{overview.model_folder ? tp('models.uninstall.modelsAuto', overview.models) : tp('models.uninstall.models', overview.models)}</span>
          )}
        </p>
      )}
      {/* Only what has a target can go now; the rest needs one chosen first. */}
      {overview && overview.unexported.length > 0 && (
        <button type="button" className="btn btn--small" disabled={busy} onClick={() => void exportAll()}>
          {busy ? t('models.auto.busy') : t('models.uninstall.exportNow')}
        </button>
      )}
    </aside>
  );
}

/**
 * "Show me where these pictures are" (doc 59).
 *
 * Sits beside every control that selects an existing dataset. A dataset is an abstraction
 * over files the user still owns, and at some point they want the files — to back them up,
 * to add more, or to check that the thing they picked is the thing they meant.
 *
 * **Tauri only.** In the browser dev mode and in Wave 16 there is no file manager to open,
 * so the button is simply absent — the same rule the folder pickers follow.
 *
 * The folder comes from the backend rather than being derived from the dataset id, because
 * the id only tells you where the *store* directory is. A dataset created without
 * `copy_images` leaves that directory empty and its pictures live wherever the user put
 * them, so opening it would show them nothing.
 */

import { useEffect, useState, type JSX } from 'react';

import { getDatasetFolder } from '../api/datasets';
import { useT } from '../i18n';
import { hasNativeDialog, revealFolder } from '../lib/dialog';

export interface RevealDatasetButtonProps {
  readonly datasetId: string;
  readonly disabled?: boolean;
}

export function RevealDatasetButton({
  datasetId,
  disabled = false,
}: RevealDatasetButtonProps): JSX.Element | null {
  // Read in an effect, not at module scope: it asks whether Tauri injected its globals,
  // and on the first render it has not.
  const { t } = useT();
  const [available, setAvailable] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setAvailable(hasNativeDialog());
  }, []);

  // Clearing on a change of dataset, not on a timer: a stale "folder is gone" against a
  // dataset the user has since switched away from is worse than no message.
  useEffect(() => {
    setError(null);
  }, [datasetId]);

  if (!available || !datasetId) return null;

  const reveal = async (): Promise<void> => {
    setBusy(true);
    setError(null);
    try {
      const target = await getDatasetFolder(datasetId);
      if (!target.exists) {
        // The store still has the boxes; the pictures have been moved or deleted. Saying
        // which is the difference between a broken button and a moved folder.
        setError(t('studio.reveal.gone', { folder: target.folder }));
        return;
      }
      await revealFolder(target.folder);
    } catch {
      setError(t('studio.reveal.error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        type="button"
        className="btn btn--small"
        disabled={disabled || busy}
        title={t('studio.reveal.title')}
        onClick={() => void reveal()}
      >
        {t(busy ? 'studio.reveal.opening' : 'studio.reveal.open')}
      </button>
      {error && (
        <span className="reveal__error" role="alert">
          {error}
        </span>
      )}
    </>
  );
}

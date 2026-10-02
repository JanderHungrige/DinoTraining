/**
 * Where a just-imported dataset lives, and how to open it (Jan, 2026-10-02: "it is not
 * clear where the downloaded dataset is located"). The folder comes from the backend, so
 * it is right for a folder, an example download and a cloud link alike.
 */

import { useEffect, useState, type JSX } from 'react';

import { getDatasetFolder } from '../api/datasets';
import { useT } from '../i18n';
import { RevealDatasetButton } from './RevealDatasetButton';

export function DatasetWhere({ datasetId, name }: { readonly datasetId: string; readonly name: string }): JSX.Element {
  const { t } = useT();
  const [folder, setFolder] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getDatasetFolder(datasetId, controller.signal)
      .then((answer) => setFolder(answer.folder))
      // The way to open it below still holds without the path.
      .catch((error: unknown) => {
        if (!controller.signal.aborted) console.warn('Dataset folder unavailable', error);
      });
    return () => controller.abort();
  }, [datasetId]);

  return (
    <>
      {folder && (
        <p className="dsimport__where">
          {t('models.import.where', { path: folder })} <RevealDatasetButton datasetId={datasetId} />
        </p>
      )}
      <p>{t('models.import.next', { name })}</p>
    </>
  );
}

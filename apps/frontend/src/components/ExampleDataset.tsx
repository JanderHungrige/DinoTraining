/**
 * The example dataset (doc 138): OSDaR23's sequence 3_fire_site_3.4, downloaded and
 * imported in one click, everything or the RGB centre camera only.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { getImportJob, importExample, listExamples, type ExampleDataset as Example, type ExampleVariant, type ImportJob } from '../api/datasetImport';
import { useImportJob } from '../hooks/useImportJob';
import { useT, type Key } from '../i18n';
import { ImportProgress, megabytes, message } from './DatasetImport';

const VARIANTS: readonly { readonly variant: ExampleVariant; readonly label: Key; readonly keeps: Key }[] = [
  { variant: 'full', label: 'models.example.full', keeps: 'models.example.keepsAll' },
  { variant: 'rgb-center', label: 'models.example.rgb', keeps: 'models.example.keepsCentre' },
];

export function ExampleDataset({ onImported }: { readonly onImported: () => void }): JSX.Element | null {
  const { t } = useT();
  const [example, setExample] = useState<Example | null>(null);
  const [job, setJob] = useState<ImportJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback((signal?: AbortSignal) => {
    listExamples(signal)
      .then(async (examples) => {
        const first = examples[0] ?? null;
        setExample(first);
        // Opened again (another sub-tab, a reload) while it runs: follow it again.
        if (first?.running_job) setJob(await getImportJob(first.running_job, signal));
      })
      .catch((failure: unknown) => {
        if (!signal?.aborted) setError(message(failure));
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const imported = useCallback(() => {
    onImported();
    load();
  }, [onImported, load]);
  useImportJob(job, setJob, imported, (failure) => setError(message(failure)));

  if (!example) return error ? <p className="dsimport__error" role="alert">{error}</p> : null;

  const start = (variant: ExampleVariant): void => {
    setError(null);
    importExample(example.example_id, variant)
      .then(setJob)
      .catch((failure: unknown) => setError(message(failure)));
  };
  const running = job?.state === 'running';
  return (
    <section className="dsimport dsexample" aria-labelledby="dsexample-title">
      <h3 id="dsexample-title" className="dsimport__title">{t('models.example.title')}</h3>
      <p className="dsimport__lead">{t('models.example.lead')}</p>
      <div className="dsexample__choices">
        {VARIANTS.map(({ variant, label, keeps }) => (
          <button key={variant} type="button" className="btn dsexample__choice" disabled={running} onClick={() => start(variant)}>
            <strong>{t(label)}</strong>
            <span>
              {example.downloaded.includes(variant)
                ? t('models.example.again')
                : `${t('models.example.size', { size: megabytes(example.download_bytes) })} · ${t(keeps)}`}
            </span>
          </button>
        ))}
      </div>
      <p className="dsimport__note">
        {t('models.example.authors')}{' '}
        <a href={example.licence_url} target="_blank" rel="noreferrer noopener">
          {t('models.example.licence', { licence: example.licence, annotations: example.annotations_licence })}
        </a>{' '}
        <a href={example.page} target="_blank" rel="noreferrer noopener">{t('models.example.source')}</a>
      </p>
      {error && <p className="dsimport__error" role="alert">{error}</p>}
      {job && <ImportProgress job={job} />}
    </section>
  );
}

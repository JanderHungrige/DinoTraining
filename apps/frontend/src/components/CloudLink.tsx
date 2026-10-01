/**
 * "Link a cloud dataset" (doc 148): a connection, a bucket and a prefix; the app reads the
 * listing and the annotation files, shows doc 136's summary, and links without
 * downloading a picture.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import { detectLink, listConnections, startLink, type CloudConnection, type LinkDetection } from '../api/cloud';
import type { ImportJob } from '../api/datasetImport';
import { useImportJob } from '../hooks/useImportJob';
import { useT } from '../i18n';
import { DetectionSummary, ImportProgress } from './DatasetImport';

function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

export function CloudLink({ onLinked }: { readonly onLinked: () => void }): JSX.Element | null {
  const { t } = useT();
  const [connections, setConnections] = useState<readonly CloudConnection[] | null>(null);
  // Only the user's choice is state; the default is the first connection (CLAUDE.md).
  const [chosen, setChosen] = useState('');
  const [bucket, setBucket] = useState('');
  const [prefix, setPrefix] = useState('');
  const [found, setFound] = useState<LinkDetection | null>(null);
  const [nameOverride, setNameOverride] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [job, setJob] = useState<ImportJob | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState('');
  const connectionId = chosen || connections?.[0]?.id || '';
  const name = nameOverride ?? found?.detection.name ?? '';

  useEffect(() => {
    const controller = new AbortController();
    listConnections(controller.signal)
      .then(setConnections)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setProblem(message(error));
      });
    return () => controller.abort();
  }, []);

  const linked = useCallback(() => onLinked(), [onLinked]);
  useImportJob(job, setJob, linked, (error) => setProblem(message(error)));

  if (!connections) return null;

  const check = async (): Promise<void> => {
    setBusy(true);
    setProblem('');
    setFound(null);
    setJob(null);
    setNameOverride(null);
    try {
      setFound(await detectLink(connectionId, bucket.trim(), prefix.trim()));
    } catch (error) {
      setProblem(message(error));
    } finally {
      setBusy(false);
    }
  };

  const link = async (): Promise<void> => {
    if (!found) return;
    setProblem('');
    try {
      setJob(await startLink(found.link_id, name.trim(), description.trim() || null));
    } catch (error) {
      setProblem(message(error));
    }
  };

  const running = job?.state === 'running';
  return (
    <section className="dsimport" aria-labelledby="cloudlink-title">
      <h3 id="cloudlink-title" className="dsimport__title">{t('cloud.link.title')}</h3>
      <p className="dsimport__lead">{t('cloud.link.lead')}</p>
      {connections.length === 0 ? (
        <p className="dsimport__note">{t('cloud.link.noConnection')}</p>
      ) : (
        <div className="dsimport__pick">
          <select aria-label={t('cloud.link.connection')} value={connectionId} onChange={(event) => setChosen(event.target.value)}>
            {connections.map((connection) => (
              <option key={connection.id} value={connection.id}>{connection.name}</option>
            ))}
          </select>
          <input type="text" aria-label={t('cloud.bucket')} placeholder={t('cloud.bucket')} value={bucket} onChange={(event) => setBucket(event.target.value)} />
          <input type="text" aria-label={t('cloud.link.prefix')} placeholder={t('cloud.link.prefix')} value={prefix} onChange={(event) => setPrefix(event.target.value)} />
          <button type="button" className="btn btn--primary btn--small" disabled={!bucket.trim() || busy || running} onClick={() => void check()}>
            {busy ? t('cloud.link.checking') : t('cloud.link.check')}
          </button>
        </div>
      )}
      {problem && <p className="dsimport__error" role="alert">{problem}</p>}
      {found && <DetectionSummary detection={found.detection} />}
      {found && !job && (
        <div className="dsimport__form">
          <label className="dsimport__field">
            {t('models.import.name')}
            <input type="text" value={name} onChange={(event) => setNameOverride(event.target.value)} />
          </label>
          <label className="dsimport__field">
            {t('models.import.description')}
            <textarea rows={2} value={description} placeholder={t('models.import.descriptionHint')} onChange={(event) => setDescription(event.target.value)} />
          </label>
          <button type="button" className="btn btn--primary" disabled={!name.trim()} onClick={() => void link()}>
            {t('cloud.link.link')}
          </button>
        </div>
      )}
      {job && <ImportProgress job={job} />}
    </section>
  );
}

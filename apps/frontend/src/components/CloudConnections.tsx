/**
 * "Cloud storage" in Models & Datasets → Datasets (doc 147): the connections, each testable
 * against a bucket, editable and removable; secrets are said to be set, never shown.
 */

import { useCallback, useEffect, useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import { deleteConnection, listConnections, testConnection, type CloudConnection, type CloudTestResult } from '../api/cloud';
import { useT, type Key } from '../i18n';
import { CloudCache } from './CloudCache';
import { CloudConnectionForm } from './CloudConnectionForm';

function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

/** `onChanged`: a connection was added, changed or removed (the link section re-reads). */
export function CloudConnections({ onChanged }: { readonly onChanged?: () => void }): JSX.Element {
  const { t } = useT();
  const [connections, setConnections] = useState<readonly CloudConnection[] | null>(null);
  const [editing, setEditing] = useState<CloudConnection | 'new' | null>(null);
  const [problem, setProblem] = useState('');

  const load = useCallback((signal?: AbortSignal) => {
    listConnections(signal)
      .then(setConnections)
      .catch((error: unknown) => {
        if (!signal?.aborted) setProblem(message(error));
      });
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const saved = (): void => {
    setEditing(null);
    load();
    onChanged?.();
  };

  return (
    <details className="dsguide__section cloud">
      <summary>{t('cloud.title')}{connections && connections.length > 0 ? ` (${connections.length})` : ''}</summary>
      <p className="dsguide__lead">{t('cloud.lead')}</p>
      {connections && connections.length === 0 && <p className="dsguide__lead">{t('cloud.empty')}</p>}
      <ul className="cloud__list">
        {connections?.map((connection) =>
          editing !== 'new' && editing?.id === connection.id ? (
            <li key={connection.id}>
              <CloudConnectionForm key={connection.id} initial={connection} onSaved={saved} onCancel={() => setEditing(null)} />
            </li>
          ) : (
            <ConnectionRow key={connection.id} connection={connection} onEdit={() => setEditing(connection)} onDeleted={() => { load(); onChanged?.(); }} />
          ),
        )}
      </ul>
      {editing === 'new' ? (
        <CloudConnectionForm key="new" initial={null} onSaved={saved} onCancel={() => setEditing(null)} />
      ) : (
        <button type="button" className="btn btn--small" onClick={() => setEditing('new')}>{t('cloud.add')}</button>
      )}
      {problem && <p className="dsimport__error" role="alert">{problem}</p>}
      <CloudCache />
    </details>
  );
}

interface RowProps {
  readonly connection: CloudConnection;
  readonly onEdit: () => void;
  readonly onDeleted: () => void;
}

function ConnectionRow({ connection, onEdit, onDeleted }: RowProps): JSX.Element {
  const { t } = useT();
  const [testing, setTesting] = useState(false);
  const [bucket, setBucket] = useState('');
  const [result, setResult] = useState<CloudTestResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const where = connection.endpoint ?? connection.account ?? t(`cloud.default.${connection.kind}` as Key);

  const test = async (): Promise<void> => {
    setBusy(true);
    setResult(null);
    try {
      setResult(await testConnection(connection.id, bucket.trim()));
    } catch (error) {
      setResult({ ok: false, message: message(error) });
    } finally {
      setBusy(false);
    }
  };

  const remove = async (): Promise<void> => {
    await deleteConnection(connection.id);
    onDeleted();
  };

  return (
    <li className="cloud__row">
      <span className="cloud__name">{connection.name}</span>
      <span className="library__meta">
        {t(`cloud.kind.${connection.kind}` as Key)} · {where} · {connection.secrets_set.length ? t('cloud.secretsSet') : t('cloud.secretsMissing')}
      </span>
      <span className="library__actions">
        <button type="button" className="btn btn--small" aria-expanded={testing} onClick={() => setTesting(!testing)}>{t('cloud.test')}</button>
        <button type="button" className="btn btn--small" onClick={onEdit}>{t('cloud.edit')}</button>
        {confirming ? (
          <>
            <button type="button" className="btn btn--small btn--danger" onClick={() => void remove()}>{t('cloud.deleteNamed', { name: connection.name })}</button>
            <button type="button" className="btn btn--small" onClick={() => setConfirming(false)}>{t('cloud.keep')}</button>
          </>
        ) : (
          <button type="button" className="btn btn--small" onClick={() => setConfirming(true)}>{t('cloud.delete')}</button>
        )}
      </span>
      {testing && (
        <div className="cloud__test">
          <input type="text" aria-label={t('cloud.bucket')} placeholder={t('cloud.bucket')} value={bucket} onChange={(event) => setBucket(event.target.value)} />
          <button type="button" className="btn btn--small btn--primary" disabled={busy || !bucket.trim()} onClick={() => void test()}>
            {busy ? t('cloud.testing') : t('cloud.testNow')}
          </button>
          {result && <p className={result.ok ? 'cloud__ok' : 'dsimport__error'} role="status">{result.message}</p>}
        </div>
      )}
    </li>
  );
}

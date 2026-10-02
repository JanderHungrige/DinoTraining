/**
 * Add or change a cloud storage connection (doc 147): the kind first, then only its fields.
 * Secrets are password fields and are never filled in: an empty one keeps what is saved.
 */

import { useState, type JSX } from 'react';

import { ApiError } from '../api/client';
import { saveConnection, SECRET_PARTS, type CloudConnection, type CloudKind } from '../api/cloud';
import { useT, type Key } from '../i18n';

const KINDS: readonly CloudKind[] = ['s3', 'azure', 'gcs'];

function message(error: unknown): string {
  return error instanceof ApiError || error instanceof Error ? error.message : String(error);
}

export interface CloudConnectionFormProps {
  /** The connection to change; null adds one. Rendered fresh per connection (a `key`). */
  readonly initial: CloudConnection | null;
  readonly onSaved: () => void;
  readonly onCancel: () => void;
}

export function CloudConnectionForm({ initial, onSaved, onCancel }: CloudConnectionFormProps): JSX.Element {
  const { t } = useT();
  const [kind, setKind] = useState<CloudKind>(initial?.kind ?? 's3');
  const [name, setName] = useState(initial?.name ?? '');
  const [endpoint, setEndpoint] = useState(initial?.endpoint ?? '');
  const [region, setRegion] = useState(initial?.region ?? '');
  const [account, setAccount] = useState(initial?.account ?? '');
  const [secrets, setSecrets] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState('');

  const setSecret = (part: string, value: string): void => setSecrets((current) => ({ ...current, [part]: value }));
  const saved = (part: string): boolean => initial?.secrets_set.includes(part) ?? false;

  const readKeyFile = async (file: File | undefined): Promise<void> => {
    if (file) setSecret('service_account', await file.text());
  };

  const save = async (): Promise<void> => {
    setBusy(true);
    setProblem('');
    try {
      const fields = {
        name: name.trim(),
        kind,
        endpoint: endpoint.trim() || null,
        region: kind === 's3' ? region.trim() || null : null,
        account: kind === 'azure' ? account.trim() || null : null,
      };
      await saveConnection(fields, secrets, initial?.id ?? null);
      onSaved();
    } catch (error) {
      setProblem(message(error));
    } finally {
      setBusy(false);
    }
  };

  const field = (label: string, value: string, onChange: (next: string) => void, placeholder?: string): JSX.Element => (
    <label className="dsimport__field">
      {label}
      <input type="text" value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );

  return (
    <div className="cloud__form" role="group" aria-label={initial ? t('cloud.edit') : t('cloud.add')}>
      <label className="dsimport__field">
        {t('cloud.form.kind')}
        <select value={kind} disabled={initial !== null} onChange={(event) => setKind(event.target.value as CloudKind)}>
          {KINDS.map((option) => (
            <option key={option} value={option}>{t(`cloud.kind.${option}` as Key)}</option>
          ))}
        </select>
      </label>
      {field(t('cloud.form.name'), name, setName)}
      {kind === 'azure' && field(t('cloud.form.account'), account, setAccount)}
      {field(t('cloud.form.endpoint', { provider: t(`cloud.default.${kind}` as Key) }), endpoint, setEndpoint, kind === 's3' ? 'http://127.0.0.1:9000' : undefined)}
      {kind === 's3' && field(t('cloud.form.region'), region, setRegion, 'us-east-1')}
      {SECRET_PARTS[kind].map((part) =>
        part === 'service_account' ? (
          <label key={part} className="dsimport__field">
            {t('cloud.form.service_account')}
            <textarea rows={3} value={secrets[part] ?? ''} placeholder={saved(part) ? t('cloud.form.keepSecret') : '{ "type": "service_account", … }'}
              onChange={(event) => setSecret(part, event.target.value)} />
            <input type="file" accept=".json,application/json" aria-label={t('cloud.form.keyFile')} onChange={(event) => void readKeyFile(event.target.files?.[0])} />
          </label>
        ) : (
          <label key={part} className="dsimport__field">
            {t(`cloud.form.${part}` as Key)}
            <input type="password" autoComplete="off" value={secrets[part] ?? ''} placeholder={saved(part) ? t('cloud.form.keepSecret') : ''}
              onChange={(event) => setSecret(part, event.target.value)} />
          </label>
        ),
      )}
      <div className="cloud__buttons">
        <button type="button" className="btn btn--primary btn--small" disabled={busy || !name.trim()} onClick={() => void save()}>
          {t('cloud.form.save')}
        </button>
        <button type="button" className="btn btn--small" onClick={onCancel}>{t('cloud.form.cancel')}</button>
      </div>
      {problem && <p className="dsimport__error" role="alert">{problem}</p>}
    </div>
  );
}

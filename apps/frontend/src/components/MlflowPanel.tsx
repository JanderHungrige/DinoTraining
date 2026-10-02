/**
 * MLflow (doc 123): where every training run and every saved model is also recorded.
 *
 * The URI, experiment and "register models" are shown; credentials are write-only — the
 * backend says only which kind is set. Test connection answers the only question that
 * matters before training: will the runs arrive?
 */

import { useEffect, useState, type FormEvent, type JSX } from 'react';

import { clearMlflowSettings, getMlflowStatus, saveMlflowSettings, testMlflow, type MlflowStatus } from '../api/mlops';
import { useT } from '../i18n';
import { MlflowBackfill } from './MlflowBackfill';

export function MlflowPanel(): JSX.Element {
  const { t } = useT();
  const [status, setStatus] = useState<MlflowStatus | null>(null);
  const [uri, setUri] = useState<string | null>(null);
  const [experiment, setExperiment] = useState<string | null>(null);
  const [register, setRegister] = useState<boolean | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [token, setToken] = useState('');
  const [said, setSaid] = useState('');
  const [problem, setProblem] = useState('');

  useEffect(() => {
    getMlflowStatus()
      .then(setStatus)
      .catch((cause: unknown) => setProblem(cause instanceof Error ? cause.message : String(cause)));
  }, []);

  // Only the user's edits are state; the shown values follow what is stored (CLAUDE.md).
  const shownUri = uri ?? status?.uri ?? '';
  const shownExperiment = experiment ?? status?.experiment ?? 'V-Rex';
  const shownRegister = register ?? status?.register_models ?? true;

  const attempt = async (work: () => Promise<string>): Promise<void> => {
    try {
      setSaid(await work());
      setProblem('');
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  const save = (event: FormEvent): Promise<void> => {
    event.preventDefault();
    return attempt(async () => {
      const next = await saveMlflowSettings({
        uri: shownUri,
        experiment: shownExperiment,
        register_models: shownRegister,
        ...(username ? { username } : {}),
        ...(password ? { password } : {}),
        ...(token ? { token } : {}),
      });
      setStatus(next);
      setPassword('');
      setToken('');
      return t('admin.mlflow.saved');
    });
  };

  const test = (): Promise<void> =>
    attempt(async () => {
      const result = await testMlflow();
      if (!result.ok) throw new Error(result.message);
      return result.message;
    });

  const disconnect = (): Promise<void> =>
    attempt(async () => {
      setStatus(await clearMlflowSettings());
      setUri(null);
      return t('admin.mlflow.disconnected');
    });

  return (
    <div className="conn__mode mlflow">
      <p className="intro__note">{t('admin.mlflow.lead')}</p>
      <p role="status">
        {status?.configured ? t('admin.mlflow.on', { uri: status.uri ?? '', experiment: status.experiment }) : t('admin.mlflow.off')}
        {status?.configured && status.auth !== 'none' && ` · ${t(status.auth === 'token' ? 'admin.mlflow.authToken' : 'admin.mlflow.authBasic')}`}
      </p>
      <form className="mlflow__form" onSubmit={(event) => void save(event)}>
        <label>
          {t('admin.mlflow.uri')}
          <input value={shownUri} placeholder="http://127.0.0.1:5001" onChange={(e) => setUri(e.target.value)} />
        </label>
        <label>
          {t('admin.mlflow.experiment')}
          <input value={shownExperiment} onChange={(e) => setExperiment(e.target.value)} />
        </label>
        <label className="mlflow__check">
          <input type="checkbox" checked={shownRegister} onChange={(e) => setRegister(e.target.checked)} />
          {t('admin.mlflow.register')}
        </label>
        <details>
          <summary>{t('admin.mlflow.credentials')}</summary>
          <p className="phrasebar__note">{t('admin.mlflow.credentialsHint')}</p>
          <label>
            {t('admin.mlflow.username')}
            <input value={username} autoComplete="off" placeholder={status?.username ?? ''} onChange={(e) => setUsername(e.target.value)} />
          </label>
          <label>
            {t('admin.mlflow.password')}
            <input type="password" value={password} autoComplete="new-password" onChange={(e) => setPassword(e.target.value)} />
          </label>
          <label>
            {t('admin.mlflow.token')}
            <input type="password" value={token} autoComplete="off" onChange={(e) => setToken(e.target.value)} />
          </label>
        </details>
        <div className="apidocs__actions">
          <button type="submit" className="btn btn--primary" disabled={!shownUri.trim()}>
            {t('admin.mlflow.save')}
          </button>
          <button type="button" className="btn" disabled={!status?.configured} onClick={() => void test()}>
            {t('admin.mlflow.test')}
          </button>
          <button type="button" className="btn" disabled={!status?.configured} onClick={() => void disconnect()}>
            {t('admin.mlflow.disconnect')}
          </button>
        </div>
      </form>
      <MlflowBackfill enabled={Boolean(status?.configured)} />
      {said && <p className="trainer__dim" role="status">{said}</p>}
      {problem && <p className="run__warn" role="alert">{problem}</p>}
    </div>
  );
}

/**
 * "Send existing models to MLflow" (doc 124): the models trained before MLflow was set up,
 * each once, with progress while it runs.
 */

import { useEffect, useState, type JSX } from 'react';

import { getBackfill, startBackfill, type BackfillJob } from '../api/mlops';
import { useT } from '../i18n';

const POLL_MS = 1000;

export function MlflowBackfill({ enabled }: { readonly enabled: boolean }): JSX.Element {
  const { t } = useT();
  const [job, setJob] = useState<BackfillJob | null>(null);
  const [problem, setProblem] = useState('');
  const running = job?.state === 'running';

  useEffect(() => {
    if (!job || job.state !== 'running') return;
    const timer = window.setTimeout(() => {
      getBackfill(job.job_id)
        .then(setJob)
        .catch((cause: unknown) => setProblem(cause instanceof Error ? cause.message : String(cause)));
    }, POLL_MS);
    return () => window.clearTimeout(timer);
  }, [job]);

  const start = async (): Promise<void> => {
    try {
      setProblem('');
      setJob(await startBackfill());
    } catch (cause) {
      setProblem(cause instanceof Error ? cause.message : String(cause));
    }
  };

  return (
    <div className="mlflow__backfill">
      <button type="button" className="btn" disabled={!enabled || running} title={t('admin.mlflow.backfillHint')} onClick={() => void start()}>
        {running ? t('admin.mlflow.backfillRunning') : t('admin.mlflow.backfill')}
      </button>
      {job && (
        <p role="status">
          {t('admin.mlflow.backfillProgress', { sent: job.sent, total: job.total, skipped: job.skipped, failed: job.failed })}
          {job.state === 'complete' && ` ${t('admin.mlflow.backfillDone')}`}
        </p>
      )}
      {job?.notes.map((note) => (
        <p key={note} className={job.state === 'failed' ? 'run__warn' : 'trainer__dim'}>
          {note}
        </p>
      ))}
      {problem && <p className="run__warn" role="alert">{problem}</p>}
    </div>
  );
}

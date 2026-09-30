/**
 * One model in the Admin tab: what it is, whether it is on disk, and the action.
 *
 * A gated model the user cannot download is shown disabled with the reason, rather
 * than hidden — "where is DINOv3?" is a worse question than "why is it greyed out?".
 *
 * **The licence is stated before the download, never after** (doc 35). It used to appear
 * only for *gated* models, in the token panel — so an ungated CC BY-NC model showed no
 * licence at all, which is the one case where not knowing actually costs something. That
 * is a Wave 8 packaging constraint surfaced early: an installable app cannot redistribute
 * a non-commercial model, and the person choosing to download one should be told first.
 */

import type { JSX } from 'react';

import type { DownloadJob, ModelInfo } from '../api/models';
import { useT } from '../i18n';

export interface ModelCardProps {
  readonly model: ModelInfo;
  readonly job: DownloadJob | undefined;
  readonly busy: boolean;
  readonly onDownload: (modelId: string) => void;
  readonly onRemove: (modelId: string) => void;
}

function percent(job: DownloadJob): number | null {
  if (job.total_bytes <= 0) return null;
  return Math.min(100, Math.round((job.downloaded_bytes / job.total_bytes) * 100));
}

function DownloadProgress({ job }: { readonly job: DownloadJob }): JSX.Element {
  const { t } = useT();
  const value = percent(job);
  const label =
    value === null
      ? t('admin.model.downloading')
      : t('admin.model.downloadingPercent', { percent: value });

  return (
    <div className="modelcard__progress">
      <div
        className="progress"
        role="progressbar"
        aria-label={label}
        {...(value === null
          ? {}
          : { 'aria-valuenow': value, 'aria-valuemin': 0, 'aria-valuemax': 100 })}
      >
        <div
          className={value === null ? 'progress__bar progress__bar--indeterminate' : 'progress__bar'}
          style={value === null ? undefined : { width: `${value}%` }}
        />
      </div>
      <span className="modelcard__progresstext">{label}</span>
    </div>
  );
}

export function ModelCard({
  model,
  job,
  busy,
  onDownload,
  onRemove,
}: ModelCardProps): JSX.Element {
  const { t } = useT();
  const downloading = job?.state === 'pending' || job?.state === 'downloading';
  const sizeLabel = model.installed
    ? t('admin.model.onDisk', { size: model.size_on_disk_mb })
    : t('admin.model.downloadSize', { size: model.approx_size_mb });

  return (
    <article className="modelcard">
      <div className="modelcard__head">
        <h4 className="modelcard__title">{model.id}</h4>
        {model.installed && (
          <span className="badge badge--installed">{t('admin.model.installed')}</span>
        )}
        {model.gated && !model.installed && <span className="badge badge--gated">{t('admin.model.gated')}</span>}
        {model.non_commercial && (
          <span
            className="badge badge--noncommercial"
            title={t('admin.model.licensed', { licence: model.licence })}
          >
            {t('admin.model.nonCommercial')}
          </span>
        )}
      </div>

      <p className="modelcard__desc">{model.description}</p>
      <p className="modelcard__meta">
        <code>{model.repo_id}</code> · {sizeLabel} ·{' '}
        <a href={model.licence_url} target="_blank" rel="noreferrer noopener">
          {model.licence}
        </a>
      </p>

      {downloading && job ? (
        <DownloadProgress job={job} />
      ) : (
        <div className="modelcard__actions">
          {model.installed ? (
            <button
              type="button"
              className="btn btn--danger"
              disabled={busy}
              onClick={() => onRemove(model.id)}
            >
              {busy ? t('admin.model.removing') : t('admin.model.remove')}
            </button>
          ) : (
            <button
              type="button"
              className="btn"
              disabled={busy || !model.available}
              onClick={() => onDownload(model.id)}
            >
              {busy ? t('admin.model.starting') : t('admin.model.download')}
            </button>
          )}
        </div>
      )}

      {!model.available && model.unavailable_reason && (
        <p className="modelcard__reason">{model.unavailable_reason}</p>
      )}
    </article>
  );
}

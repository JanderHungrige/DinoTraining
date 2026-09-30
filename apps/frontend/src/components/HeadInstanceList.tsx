/**
 * Heads the user has trained or imported.
 *
 * Renders `summary` from the backend rather than composing a description locally — the
 * same head must read identically here, in the Inference Viewer and in the Generator.
 */

import type { JSX } from 'react';

import { KIND_LABELS, type HeadInstanceInfo } from '../api/headInstances';
import { useT } from '../i18n';

export interface HeadInstanceListProps {
  readonly heads: readonly HeadInstanceInfo[];
  readonly busy: Readonly<Record<string, boolean>>;
  readonly onDelete: (id: string) => void;
}

export function HeadInstanceList({ heads, busy, onDelete }: HeadInstanceListProps): JSX.Element {
  const { t } = useT();
  if (heads.length === 0) {
    return <p className="trainer__empty">{t('training.heads.empty')}</p>;
  }

  return (
    <ul className="heads">
      {heads.map((head) => (
        <li key={head.id} className="heads__item">
          <div className="heads__body">
            <strong className="heads__name">{head.name}</strong>
            <span className="badge">{t(KIND_LABELS[head.kind])}</span>
            <p className="heads__summary">{head.summary}</p>
            <p className="trainer__dim">
              {t('training.heads.backbone', { id: head.backbone_id })}
              {head.best_epoch !== null && ` · ${t('training.heads.bestEpoch', { epoch: head.best_epoch })}`}
              {head.epochs_trained > 0 && ` ${t('training.heads.ofTotal', { total: head.epochs_trained })}`}
            </p>
          </div>
          <button
            className="btn btn--danger"
            type="button"
            disabled={busy[head.id] === true}
            onClick={() => onDelete(head.id)}
          >
            {t('training.heads.delete')}
          </button>
        </li>
      ))}
    </ul>
  );
}

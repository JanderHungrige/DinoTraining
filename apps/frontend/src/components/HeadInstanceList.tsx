/**
 * Heads the user has trained or imported.
 *
 * Renders `summary` from the backend rather than composing a description locally — the
 * same head must read identically here, in the Inference Viewer and in the Generator.
 */

import type { JSX } from 'react';

import { KIND_LABELS, type HeadInstanceInfo } from '../api/headInstances';

export interface HeadInstanceListProps {
  readonly heads: readonly HeadInstanceInfo[];
  readonly busy: Readonly<Record<string, boolean>>;
  readonly onDelete: (id: string) => void;
}

export function HeadInstanceList({ heads, busy, onDelete }: HeadInstanceListProps): JSX.Element {
  if (heads.length === 0) {
    return <p className="trainer__empty">No trained heads yet. Start a run above.</p>;
  }

  return (
    <ul className="heads">
      {heads.map((head) => (
        <li key={head.id} className="heads__item">
          <div className="heads__body">
            <strong className="heads__name">{head.name}</strong>
            <span className="badge">{KIND_LABELS[head.kind]}</span>
            <p className="heads__summary">{head.summary}</p>
            <p className="trainer__dim">
              backbone {head.backbone_id}
              {head.best_epoch !== null && ` · best epoch ${head.best_epoch}`}
              {head.epochs_trained > 0 && ` of ${head.epochs_trained}`}
            </p>
          </div>
          <button
            className="btn btn--danger"
            type="button"
            disabled={busy[head.id] === true}
            onClick={() => onDelete(head.id)}
          >
            Delete
          </button>
        </li>
      ))}
    </ul>
  );
}

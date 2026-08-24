/**
 * One downloadable default head in the Admin tab.
 *
 * An incompatible entry is shown with its reason rather than hidden or greyed out
 * without explanation. That is the wave rule: "why can't I use this?" always has an
 * answer on screen, and the answer usually names the backbone to download next.
 */

import type { JSX } from 'react';

import { formatSize, type CatalogEntry } from '../api/headCatalog';

export interface HeadCatalogCardProps {
  readonly entry: CatalogEntry;
  readonly busy: boolean;
  readonly onInstall: (entryId: string) => void;
}

/** Why the install button is unavailable, or null when it is not. */
function blockedReason(entry: CatalogEntry): string | null {
  if (entry.installed) return null;
  if (!entry.backbone_installed) {
    return `Download the ${entry.backbone_id} backbone first.`;
  }
  if (entry.compatible === false) {
    return entry.incompatible_reason ?? 'Not compatible with the selected backbone.';
  }
  return null;
}

export function HeadCatalogCard({ entry, busy, onInstall }: HeadCatalogCardProps): JSX.Element {
  const blocked = blockedReason(entry);
  const classes = entry.num_classes === null ? null : `${entry.num_classes} classes`;

  return (
    <article className="headcard">
      <div className="headcard__head">
        <h4 className="headcard__title">{entry.title}</h4>
        {entry.installed && <span className="badge badge--installed">Installed</span>}
      </div>

      <p className="headcard__desc">{entry.trained_on}</p>
      <p className="headcard__meta">
        <code>{entry.backbone_id}</code> · {formatSize(entry.size_bytes)} · {entry.licence}
        {classes ? ` · ${classes}` : ''}
      </p>

      <div className="headcard__actions">
        {entry.installed ? (
          <span className="headcard__done">Ready to use in the Inference Viewer</span>
        ) : (
          <button
            type="button"
            className="btn"
            disabled={busy || blocked !== null}
            onClick={() => onInstall(entry.id)}
          >
            {busy ? 'Installing…' : 'Install'}
          </button>
        )}
      </div>

      {blocked && <p className="headcard__reason">{blocked}</p>}
    </article>
  );
}

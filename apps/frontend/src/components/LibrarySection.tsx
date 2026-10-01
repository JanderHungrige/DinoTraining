/**
 * One list of the Library (doc 51): datasets, heads or fine-tuned models, each row with its
 * checkbox and two-click delete — and, for trained models, extra actions (doc 121).
 * Split out of the Library tab at the 300-line gate.
 */

import type { JSX, ReactNode } from 'react';

import type { LibraryKind } from '../hooks/useLibrary';
import { useT } from '../i18n';

export interface Row {
  readonly id: string;
  readonly name: string;
  readonly detail: string;
  readonly meta: string;
  /** Doc 136: a dataset's description, under its parameters. */
  readonly note?: string | null;
}

export interface SectionProps {
  readonly title: string;
  readonly empty: string;
  readonly rows: readonly Row[];
  readonly kind: LibraryKind;
  readonly selected: ReadonlySet<string>;
  readonly onToggle: (kind: LibraryKind, id: string) => void;
  readonly confirming: string | null;
  readonly onConfirm: (id: string | null) => void;
  readonly busyId: string | null;
  readonly onDelete: (kind: LibraryKind, id: string) => Promise<void>;
  /** Doc 121: more actions for a row (Export, Show where it is). */
  readonly actions?: (row: Row) => ReactNode;
}

export function Section({
  title,
  empty,
  rows,
  kind,
  selected,
  onToggle,
  confirming,
  onConfirm,
  busyId,
  onDelete,
  actions,
}: SectionProps): JSX.Element {
  const { t } = useT();
  return (
    <section className="library__section">
      <h3 className="library__heading">
        {title} <span className="library__count">{rows.length}</span>
      </h3>

      {rows.length === 0 ? (
        <p className="library__empty">{empty}</p>
      ) : (
        <ul className="library__list">
          {rows.map((row) => (
            <li key={row.id} className="library__row">
              <input
                type="checkbox"
                className="library__pick"
                checked={selected.has(`${kind}:${row.id}`)}
                disabled={busyId !== null}
                // Name *and* detail: four heads here are all called "Object detection:
                // dog, person" and differ only by what they were trained on and their
                // mAP. Identical labels on four checkboxes is a real ambiguity for
                // anyone not reading the row visually.
                aria-label={t('admin.library.selectRow', { name: row.name, detail: row.detail })}
                onChange={() => onToggle(kind, row.id)}
              />
              <span className="library__name">{row.name}</span>
              {/* The description belongs to the parameters' cell: as a cell of its own it
                  pushed every later one into the wrong column (found in doc 143). */}
              <span className="library__detail">
                {row.detail}
                {row.note && <span className="library__note">{row.note}</span>}
              </span>
              <span className="library__meta">{row.meta}</span>
              {actions?.(row)}
              {/* Two clicks, not a browser confirm(): a modal cannot say *which* item it
                  is about, and this list is full of similarly-named things. */}
              {confirming === row.id ? (
                <span className="library__confirm">
                  <button
                    type="button"
                    className="btn btn--small btn--danger"
                    disabled={busyId !== null}
                    onClick={() => {
                      onConfirm(null);
                      void onDelete(kind, row.id);
                    }}
                  >
                    {t('admin.library.deleteNamed', { name: row.name })}
                  </button>
                  <button
                    type="button"
                    className="btn btn--small"
                    onClick={() => onConfirm(null)}
                  >
                    {t('admin.library.keep')}
                  </button>
                </span>
              ) : (
                <button
                  type="button"
                  className="btn btn--small"
                  disabled={busyId !== null}
                  aria-label={t('admin.library.deleteRow', { name: row.name })}
                  onClick={() => onConfirm(row.id)}
                >
                  {busyId === row.id ? t('admin.library.deleting') : t('admin.library.delete')}
                </button>
              )}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

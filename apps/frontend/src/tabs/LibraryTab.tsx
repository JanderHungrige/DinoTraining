/**
 * Everything you have made (doc 51).
 *
 * Datasets, trained heads and fine-tuned models were each reachable only from the tab that
 * produced them, and two of the three had no way to delete anything. "What do I have, and
 * what can I throw away?" is one question; this is the one place that answers it.
 *
 * Read-only apart from delete, deliberately. Renaming would need routes that do not exist
 * and a rule about what a rename does to provenance already recorded inside trained heads.
 */

import { useState, type JSX } from 'react';

import { BULK, useLibrary, type LibraryKind, type LibraryTarget } from '../hooks/useLibrary';
import { useT } from '../i18n';

interface Row {
  readonly id: string;
  readonly name: string;
  readonly detail: string;
  readonly meta: string;
}

export function LibraryTab(): JSX.Element {
  const library = useLibrary();
  const { t, tp } = useT();
  const [confirming, setConfirming] = useState<string | null>(null);
  // Keyed by `kind:id`, because ids are opaque and three stores answer to them — a bare id
  // could name a dataset and a head at once and nothing would notice.
  const [selected, setSelected] = useState<ReadonlySet<string>>(new Set());
  const [confirmingBulk, setConfirmingBulk] = useState(false);

  const datasetName = (id: string): string =>
    library.datasets.find((entry) => entry.id === id)?.name ?? id.slice(0, 8);

  const toggle = (kind: LibraryKind, id: string): void => {
    const key = `${kind}:${id}`;
    setSelected((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
    setConfirmingBulk(false);
  };

  const datasetRows: Row[] = library.datasets.map((entry) => ({
    id: entry.id,
    name: entry.name,
    detail: `${tp('admin.library.images', entry.counts.images)} · ${tp(
      'admin.library.boxes',
      entry.counts.positive + entry.counts.negative + entry.counts.unclear,
    )}`,
    meta: new Date(entry.created_at).toLocaleDateString(),
  }));

  const headRows: Row[] = library.heads.map((entry) => ({
    id: entry.id,
    name: entry.name,
    // The head's own `summary`, never a second description composed here — doc 12's rule,
    // and what stops the same head reading differently in two places.
    detail: entry.summary,
    // Resolved to names, because an id tells the user nothing about which data it saw.
    meta: entry.dataset_ids.length
      ? t('admin.library.from', { names: entry.dataset_ids.map(datasetName).join(', ') })
      : entry.backbone_id,
  }));

  const finetuneRows: Row[] = library.finetunes.map((entry) => ({
    id: entry.id,
    name: entry.title,
    detail: entry.description,
    meta: entry.licence,
  }));

  const targets: LibraryTarget[] = [
    ...datasetRows.map((row) => ({ kind: 'dataset' as const, id: row.id, name: row.name })),
    ...headRows.map((row) => ({ kind: 'head' as const, id: row.id, name: row.name })),
    ...finetuneRows.map((row) => ({ kind: 'finetune' as const, id: row.id, name: row.name })),
  ].filter((target) => selected.has(`${target.kind}:${target.id}`));

  return (
    <section className="library">
      <h2 className="library__title">{t('admin.library.title')}</h2>
      <p className="library__lead">{t('admin.library.lead')}</p>

      {library.error && (
        <p className="admin__error" role="alert">
          {library.error}
        </p>
      )}

      {targets.length > 0 && (
        <div className="library__bulk" role="group" aria-label={t('admin.library.selectedGroup')}>
          <span>
            <strong>{targets.length}</strong> {t('admin.library.selected')}
          </span>
          {confirmingBulk ? (
            <>
              <button
                type="button"
                className="btn btn--small btn--danger"
                disabled={library.busyId !== null}
                onClick={() => {
                  setConfirmingBulk(false);
                  setSelected(new Set());
                  void library.removeMany(targets);
                }}
              >
                {t('admin.library.deleteMany', { count: targets.length })}
              </button>
              <button
                type="button"
                className="btn btn--small"
                onClick={() => setConfirmingBulk(false)}
              >
                {t('admin.library.keepThem')}
              </button>
            </>
          ) : (
            <button
              type="button"
              className="btn btn--small"
              disabled={library.busyId !== null}
              onClick={() => setConfirmingBulk(true)}
            >
              {library.busyId === BULK ? t('admin.library.deleting') : t('admin.library.deleteSelected')}
            </button>
          )}
          <button
            type="button"
            className="btn btn--small"
            onClick={() => setSelected(new Set())}
          >
            {t('admin.library.clearSelection')}
          </button>
          {/* Named in full while the confirmation is up: eleven checkboxes are easy to
              mis-tick, and this is the last chance to notice. */}
          {confirmingBulk && (
            <p className="library__bulknames">{targets.map((t) => t.name).join(', ')}</p>
          )}
        </div>
      )}

      {library.loading ? (
        <p role="status">{t('admin.library.loading')}</p>
      ) : (
        <>
          <Section
            title={t('admin.library.datasets')}
            empty={t('admin.library.datasetsEmpty')}
            rows={datasetRows}
            kind="dataset"
            selected={selected}
            onToggle={toggle}
            confirming={confirming}
            onConfirm={setConfirming}
            busyId={library.busyId}
            onDelete={library.remove}
          />
          <Section
            title={t('admin.library.heads')}
            empty={t('admin.library.headsEmpty')}
            rows={headRows}
            kind="head"
            selected={selected}
            onToggle={toggle}
            confirming={confirming}
            onConfirm={setConfirming}
            busyId={library.busyId}
            onDelete={library.remove}
          />
          <Section
            title={t('admin.library.finetunes')}
            empty={t('admin.library.finetunesEmpty')}
            rows={finetuneRows}
            kind="finetune"
            selected={selected}
            onToggle={toggle}
            confirming={confirming}
            onConfirm={setConfirming}
            busyId={library.busyId}
            onDelete={library.remove}
          />
        </>
      )}
    </section>
  );
}

interface SectionProps {
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
}

function Section({
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
              <span className="library__detail">{row.detail}</span>
              <span className="library__meta">{row.meta}</span>
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

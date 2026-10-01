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
import { useDatasetProfiles } from '../hooks/useDatasetProfiles';
import { annotationTypes } from '../components/DatasetImport';
import type { DatasetProfile } from '../api/datasetImport';
import type { Translator } from '../i18n';
import { useT } from '../i18n';
import { Section, type Row } from '../components/LibrarySection';
import { ModelExportActions } from '../components/ModelExportActions';

const ALL_KINDS: readonly LibraryKind[] = ['dataset', 'head', 'finetune'];

/** Doc 136: "1 284 pictures · 1 102 annotated · 3 classes · boxes, masks · video". */
function profileLine(profile: DatasetProfile, t: Translator['t'], tp: Translator['tp']): string {
  return [
    tp('models.import.pictures', profile.pictures),
    tp('models.import.annotated', profile.annotated_pictures),
    tp('models.import.classes', profile.classes.length),
    annotationTypes(profile.annotation_types, t) || null,
    t(`models.profile.media.${profile.media}`),
  ]
    .filter((part): part is string => Boolean(part))
    .join(' · ');
}

interface LibraryTabProps {
  /** Doc 135: the Models & Datasets sub-tabs each show their part (default: all). */
  readonly kinds?: readonly LibraryKind[];
  /** Doc 135: inside a sub-tab, the sub-tab names the list; no heading of its own. */
  readonly headed?: boolean;
}

export function LibraryTab({ kinds = ALL_KINDS, headed = true }: LibraryTabProps): JSX.Element {
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

  const profiles = useDatasetProfiles(kinds.includes('dataset'), library.datasets.map((d) => d.id).join());
  const datasetRows: Row[] = library.datasets.map((entry) => {
    const profile = profiles.get(entry.id);
    return {
      id: entry.id,
      name: entry.name,
      detail: profile
        ? profileLine(profile, t, tp)
        : `${tp('admin.library.images', entry.counts.images)} · ${tp(
            'admin.library.boxes',
            entry.counts.positive + entry.counts.negative + entry.counts.unclear,
          )}`,
      meta: new Date(entry.created_at).toLocaleDateString(),
      note: profile?.description ?? null,
    };
  });

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

  const shows = (kind: LibraryKind): boolean => kinds.includes(kind);
  const targets: LibraryTarget[] = [
    ...datasetRows.map((row) => ({ kind: 'dataset' as const, id: row.id, name: row.name })),
    ...headRows.map((row) => ({ kind: 'head' as const, id: row.id, name: row.name })),
    ...finetuneRows.map((row) => ({ kind: 'finetune' as const, id: row.id, name: row.name })),
  ].filter((target) => shows(target.kind) && selected.has(`${target.kind}:${target.id}`));

  return (
    <section className="library">
      {headed && (
        <>
          <h2 className="library__title">{t('admin.library.title')}</h2>
          <p className="library__lead">{t('admin.library.lead')}</p>
        </>
      )}

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
          {shows('dataset') && <Section
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
          />}
          {shows('head') && <Section
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
            actions={(row) => <ModelExportActions kind="heads" instanceId={row.id} name={row.name} />}
          />}
          {shows('finetune') && <Section
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
            actions={(row) => <ModelExportActions kind="finetuned" instanceId={row.id} name={row.name} />}
          />}
        </>
      )}
    </section>
  );
}

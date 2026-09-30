/**
 * Step 3: safe fixes (doc 83). Nothing is deleted: pictures are left out and can be put
 * back, and classes are mapped for training while the stored names stay as they were.
 */

import { useState, type JSX } from 'react';

import type { DatasetAudit, FixAction, PrepState } from '../../api/prep';
import { useT } from '../../i18n';

export interface FixStepProps {
  readonly audit: DatasetAudit | null;
  readonly state: PrepState | null;
  readonly busy: boolean;
  readonly onFix: (
    action: FixAction,
    extra?: { paths?: readonly string[]; class_map?: Readonly<Record<string, string | null>> },
  ) => Promise<number>;
}

interface Row {
  readonly to: string;
  readonly drop: boolean;
}

/** Only the rows the user edited; everything else reads from the saved map. */
type Drafts = Readonly<Record<string, Row>>;

function savedRow(name: string, map: Readonly<Record<string, string | null>>): Row {
  if (!(name in map)) return { to: name, drop: false };
  const to = map[name];
  return to === null || to === undefined ? { to: name, drop: true } : { to, drop: false };
}

function ClassRow(props: {
  readonly name: string;
  readonly count: number | undefined;
  readonly row: Row;
  readonly onEdit: (change: Partial<Row>) => void;
}): JSX.Element {
  const { name, count, row, onEdit } = props;
  const { t } = useT();
  return (
    <tr>
      <td>{name}</td>
      <td>{count ?? '—'}</td>
      <td>
        <input
          aria-label={t('prepare.fix.trainNameAs', { name })}
          value={row.to}
          disabled={row.drop}
          onChange={(event) => onEdit({ to: event.target.value })}
        />
      </td>
      <td>
        <input
          type="checkbox"
          aria-label={t('prepare.fix.leaveOutName', { name })}
          checked={row.drop}
          onChange={(event) => onEdit({ drop: event.target.checked })}
        />
      </td>
    </tr>
  );
}

function ClassMap({ audit, state, busy, onFix }: FixStepProps & { readonly state: PrepState }): JSX.Element {
  const { t } = useT();
  const [drafts, setDrafts] = useState<Drafts>({});
  const counts = audit?.summary.classes ?? {};
  const names = [...new Set([...Object.keys(counts), ...Object.keys(state.class_map)])].sort();
  const row = (name: string): Row => drafts[name] ?? savedRow(name, state.class_map);
  const edit = (name: string, change: Partial<Row>): void =>
    setDrafts((previous) => ({ ...previous, [name]: { ...row(name), ...change } }));

  const save = async (): Promise<void> => {
    const map: Record<string, string | null> = {};
    for (const name of names) {
      const { to, drop } = row(name);
      if (drop) map[name] = null;
      else if (to.trim() && to.trim() !== name) map[name] = to.trim();
    }
    await onFix('set-class-map', { class_map: map });
    setDrafts({});
  };

  return (
    <fieldset className="prep-classmap">
      <legend>{t('prepare.fix.classesLegend')}</legend>
      <p className="prep-step__hint">{t('prepare.fix.classesHint')}</p>
      <table>
        <thead>
          <tr>
            <th>{t('prepare.table.class')}</th>
            <th>{t('prepare.table.examples')}</th>
            <th>{t('prepare.fix.trainAs')}</th>
            <th>{t('prepare.fix.leaveOut')}</th>
          </tr>
        </thead>
        <tbody>
          {names.map((name) => (
            <ClassRow key={name} name={name} count={counts[name]} row={row(name)} onEdit={(change) => edit(name, change)} />
          ))}
        </tbody>
      </table>
      <button type="button" className="btn" disabled={busy || Object.keys(drafts).length === 0} onClick={() => void save()}>
        {t('prepare.fix.saveClasses')}
      </button>
    </fieldset>
  );
}

export function FixStep(props: FixStepProps): JSX.Element {
  const { audit, state, busy, onFix } = props;
  const { t, tp } = useT();
  const [done, setDone] = useState('');
  const run = async (action: FixAction, paths?: readonly string[]): Promise<void> => {
    const changed = await onFix(action, paths ? { paths } : {});
    setDone(tp(action === 'include' ? 'prepare.fix.putBackDone' : 'prepare.fix.leftOut', changed));
  };
  const copies = audit?.copy_groups.length ?? 0;
  const unreadable = audit?.unreadable.length ?? 0;
  const excluded = state?.excluded ?? [];
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        {t('prepare.fix.why')}
      </p>
      <div className="prep-step__actions">
        <button type="button" className="btn" disabled={busy || copies === 0} onClick={() => void run('exclude-copies')}>
          {tp('prepare.fix.copies', copies)}
        </button>
        <button type="button" className="btn" disabled={busy || unreadable === 0} onClick={() => void run('exclude-unreadable')}>
          {t('prepare.fix.unreadable', { count: unreadable })}
        </button>
        <button type="button" className="btn" disabled={busy || excluded.length === 0} onClick={() => void run('include', excluded)}>
          {tp('prepare.fix.putBack', excluded.length)}
        </button>
      </div>
      {done && (
        <p role="status" className="prep-step__status">
          {done} {t('prepare.fix.again')}
        </p>
      )}
      {!audit && <p className="prep-step__note">{t('prepare.fix.auditFirst')}</p>}
      {state && <ClassMap {...props} state={state} />}
    </div>
  );
}

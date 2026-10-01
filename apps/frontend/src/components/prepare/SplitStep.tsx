/**
 * Step 4: the split (doc 84). Frames of one video and photos of one scene stay together,
 * so the test score measures learning rather than memory.
 */

import type { JSX } from 'react';

import type { SplitReport } from '../../api/prep';
import { useT, type Key } from '../../i18n';

const SIDES = ['train', 'val', 'test'] as const;
const SIDE_LABEL: Readonly<Record<(typeof SIDES)[number], Key>> = {
  train: 'prepare.split.train',
  val: 'prepare.split.val',
  test: 'prepare.split.test',
};

export interface SplitStepProps {
  readonly split: SplitReport | null;
  readonly busy: boolean;
  readonly onSplit: (mode: 'auto' | 'keep-source') => void;
}

function Sides({ split }: { readonly split: SplitReport }): JSX.Element {
  const { t } = useT();
  const classes = [...new Set(SIDES.flatMap((side) => Object.keys(split.sides[side].classes)))].sort();
  return (
    <table className="prep-table">
      <thead>
        <tr>
          <th />
          {SIDES.map((side) => (
            <th key={side}>{t(SIDE_LABEL[side])}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">{t('prepare.table.pictures')}</th>
          {SIDES.map((side) => (
            <td key={side}>{split.sides[side].images}</td>
          ))}
        </tr>
        {classes.map((name) => (
          <tr key={name}>
            <th scope="row">{name}</th>
            {SIDES.map((side) => (
              <td key={side} className={split.sides[side].classes[name] ? '' : 'prep-table__missing'}>
                {split.sides[side].classes[name] ?? 0}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function SplitStep({ split, busy, onSplit }: SplitStepProps): JSX.Element {
  const { t } = useT();
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        {t('prepare.split.why')}
      </p>
      <div className="prep-step__actions">
        <button type="button" className="btn btn--primary" disabled={busy} onClick={() => onSplit('auto')}>
          {split ? t('prepare.split.again') : t('prepare.split.auto')}
        </button>
        <button type="button" className="btn" disabled={busy} onClick={() => onSplit('keep-source')}>
          {t('prepare.split.keep')}
        </button>
      </div>
      {split && (
        <>
          <Sides split={split} />
          {split.buffer > 0 && (
            <p className="prep-step__hint">{t('prepare.split.buffer', { count: split.buffer })}</p>
          )}
          {split.warnings.map((warning) => (
            <p key={warning} className="prep-step__note">
              {warning}
            </p>
          ))}
        </>
      )}
    </div>
  );
}

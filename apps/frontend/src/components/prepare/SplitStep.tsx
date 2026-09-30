/**
 * Step 4: the split (doc 84). Frames of one video and photos of one scene stay together,
 * so the test score measures learning rather than memory.
 */

import type { JSX } from 'react';

import type { SplitReport } from '../../api/prep';

const SIDES = ['train', 'val', 'test'] as const;
const SIDE_LABEL = { train: 'Training', val: 'Validation', test: 'Test' } as const;

export interface SplitStepProps {
  readonly split: SplitReport | null;
  readonly busy: boolean;
  readonly onSplit: (mode: 'auto' | 'keep-source') => void;
}

function Sides({ split }: { readonly split: SplitReport }): JSX.Element {
  const classes = [...new Set(SIDES.flatMap((side) => Object.keys(split.sides[side].classes)))].sort();
  return (
    <table className="prep-table">
      <thead>
        <tr>
          <th />
          {SIDES.map((side) => (
            <th key={side}>{SIDE_LABEL[side]}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        <tr>
          <th scope="row">Pictures</th>
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
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        The model learns from the training pictures and is scored on pictures it has never seen.
        If a near-copy of a test picture is in training — the next frame of a video, another photo
        of the same scene — the score measures memory, not learning. So frames and scenes are kept
        together, and frames right at a boundary are set aside.
      </p>
      <div className="prep-step__actions">
        <button type="button" className="btn btn--primary" disabled={busy} onClick={() => onSplit('auto')}>
          {split ? 'Split again' : 'Split automatically (recommended)'}
        </button>
        <button type="button" className="btn" disabled={busy} onClick={() => onSplit('keep-source')}>
          Keep the split the dataset came with
        </button>
      </div>
      {split && (
        <>
          <Sides split={split} />
          {split.buffer > 0 && (
            <p className="prep-step__hint">
              {split.buffer} frame(s) beside a boundary are set aside: too close to frames on the
              other side to be fair either way.
            </p>
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

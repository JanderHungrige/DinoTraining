/**
 * What proposes the annotations, in the Dataset Generator (doc 42).
 *
 * Extracted when a third source arrived and the form crossed the 300-line gate for the
 * second time — Wave 4 split it once already. As in the Studio's picker, the options are
 * data because the *order* is a recommendation: it runs from "needs nothing" to "needs a
 * model you trained", so the first entry is the only one a new user can reach.
 */

import type { JSX } from 'react';

export type GeneratorMode = 'foundation' | 'expert' | 'masks';

interface ModeOption {
  readonly mode: GeneratorMode;
  readonly label: string;
}

export const GENERATOR_MODES: readonly ModeOption[] = Object.freeze([
  {
    mode: 'foundation',
    label: 'A general detector — finds everyday objects, nothing to set up',
  },
  { mode: 'expert', label: 'A head you trained — proposes boxes' },
  { mode: 'masks', label: 'Grounded SAM — type a concept, get masks' },
]);

export interface GeneratorModePickerProps {
  readonly mode: GeneratorMode;
  readonly onChange: (mode: GeneratorMode) => void;
}

export function GeneratorModePicker({
  mode,
  onChange,
}: GeneratorModePickerProps): JSX.Element {
  return (
    <fieldset className="genpanel__modes">
      <legend>What proposes the annotations</legend>
      {GENERATOR_MODES.map((option) => (
        <label key={option.mode} className="genpanel__mode">
          <input
            type="radio"
            name="generator-mode"
            checked={mode === option.mode}
            onChange={() => onChange(option.mode)}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </fieldset>
  );
}

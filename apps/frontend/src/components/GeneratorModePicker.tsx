/**
 * What proposes the annotations, in the Dataset Generator (doc 42).
 *
 * Extracted when a third source arrived and the form crossed the 300-line gate for the
 * second time — Wave 4 split it once already. As in the Studio's picker, the options are
 * data because the *order* is a recommendation: it runs from "needs nothing" to "needs a
 * model you trained", so the first entry is the only one a new user can reach.
 */

import type { JSX } from 'react';

import { useT, type Key } from '../i18n';

export type GeneratorMode = 'foundation' | 'expert' | 'masks';

interface ModeOption {
  readonly mode: GeneratorMode;
  /** A catalogue key, translated where it is rendered. */
  readonly label: Key;
}

export const GENERATOR_MODES: readonly ModeOption[] = Object.freeze([
  { mode: 'foundation', label: 'generator.mode.foundation' },
  { mode: 'expert', label: 'generator.mode.expert' },
  { mode: 'masks', label: 'generator.mode.masks' },
]);

export interface GeneratorModePickerProps {
  readonly mode: GeneratorMode;
  readonly onChange: (mode: GeneratorMode) => void;
}

export function GeneratorModePicker({
  mode,
  onChange,
}: GeneratorModePickerProps): JSX.Element {
  const { t } = useT();
  return (
    <fieldset className="genpanel__modes">
      <legend>{t('generator.mode.legend')}</legend>
      {GENERATOR_MODES.map((option) => (
        <label key={option.mode} className="genpanel__mode">
          <input
            type="radio"
            name="generator-mode"
            checked={mode === option.mode}
            onChange={() => onChange(option.mode)}
          />
          <span>{t(option.label)}</span>
        </label>
      ))}
    </fieldset>
  );
}

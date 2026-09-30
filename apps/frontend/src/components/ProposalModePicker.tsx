/**
 * Choosing what proposes the boxes (doc 42).
 *
 * Extracted from `SessionSetup` when a third mode arrived and the form crossed the
 * project's 300-line gate. The options are data rather than markup because the *order*
 * carries a recommendation — a general detector needs nothing set up, a prompt needs a
 * phrase, a trained head needs training to have happened — and that ordering is easier to
 * argue about in a list than in JSX.
 */

import type { JSX } from 'react';

import { useT, type Key } from '../i18n';

export type ProposalMode = 'foundation' | 'prompt' | 'head';

interface ModeOption {
  readonly mode: ProposalMode;
  readonly label: Key;
}

/**
 * Ordered by how much the user must already have. A first-time user can only use the
 * first one, so it leads.
 */
export const PROPOSAL_MODES: readonly ModeOption[] = Object.freeze([
  { mode: 'foundation', label: 'studio.mode.foundation' },
  { mode: 'prompt', label: 'studio.mode.prompt' },
  { mode: 'head', label: 'studio.mode.head' },
]);

export interface ProposalModePickerProps {
  readonly mode: ProposalMode;
  readonly onChange: (mode: ProposalMode) => void;
  readonly groupName?: string;
  readonly legend?: string;
}

export function ProposalModePicker({
  mode,
  onChange,
  groupName = 'studio-mode',
  legend,
}: ProposalModePickerProps): JSX.Element {
  const { t } = useT();
  return (
    <fieldset className="setup__modes">
      <legend>{legend ?? t('studio.mode.legend')}</legend>
      {PROPOSAL_MODES.map((option) => (
        <label key={option.mode}>
          <input
            type="radio"
            name={groupName}
            value={option.mode}
            checked={mode === option.mode}
            onChange={() => onChange(option.mode)}
          />
          <span>{t(option.label)}</span>
        </label>
      ))}
    </fieldset>
  );
}

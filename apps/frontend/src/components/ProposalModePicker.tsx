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

export type ProposalMode = 'foundation' | 'prompt' | 'head';

interface ModeOption {
  readonly mode: ProposalMode;
  readonly label: string;
}

/**
 * Ordered by how much the user must already have. A first-time user can only use the
 * first one, so it leads.
 */
export const PROPOSAL_MODES: readonly ModeOption[] = Object.freeze([
  {
    mode: 'foundation',
    label: 'A general detector — finds everyday objects, nothing to set up',
  },
  { mode: 'prompt', label: 'Grounding DINO — describe what you are looking for' },
  { mode: 'head', label: 'A head you trained — proposes boxes for its own classes' },
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
  legend = 'What proposes the boxes',
}: ProposalModePickerProps): JSX.Element {
  return (
    <fieldset className="setup__modes">
      <legend>{legend}</legend>
      {PROPOSAL_MODES.map((option) => (
        <label key={option.mode}>
          <input
            type="radio"
            name={groupName}
            value={option.mode}
            checked={mode === option.mode}
            onChange={() => onChange(option.mode)}
          />
          <span>{option.label}</span>
        </label>
      ))}
    </fieldset>
  );
}

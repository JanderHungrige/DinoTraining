/**
 * The mask-mode fields of the Dataset Generator's setup form (doc 42).
 *
 * Extracted, unchanged, when a third proposal source pushed `GeneratorSetup` past the
 * project's 300-line gate for the second time. Wave 4 split that form once already, which
 * is the signal that "the setup form" is really several forms sharing a destination.
 *
 * Renders nothing outside mask mode, so the caller reads as one line rather than a guard
 * wrapped round a block.
 */

import type { JSX } from 'react';

import type { AnnotatorInfo, PromptStyle } from '../api/annotators';
import { FieldHint } from './FieldHint';
import type { GeneratorMode } from './GeneratorModePicker';

export interface MaskSourceFieldsProps {
  readonly mode: GeneratorMode;
  readonly annotators: readonly AnnotatorInfo[];
  readonly annotatorId: string;
  readonly onAnnotatorChange: (id: string) => void;
  readonly concept: string;
  readonly onConceptChange: (concept: string) => void;
  /** Wording for the concept field. Comes from the annotator's catalogue row. */
  readonly promptStyle: PromptStyle;
}

export function MaskSourceFields({
  mode,
  annotators,
  annotatorId,
  onAnnotatorChange,
  concept,
  onConceptChange,
  promptStyle,
}: MaskSourceFieldsProps): JSX.Element | null {
  if (mode !== 'masks') return null;

  return (
        <div className="genpanel__group">
          {annotators.length > 1 && (
            <label className="genpanel__field">
              <span>Annotator</span>
              <select
                value={annotatorId}
                onChange={(event) => onAnnotatorChange(event.target.value)}
              >
                {annotators.map((annotator) => (
                  <option key={annotator.id} value={annotator.id}>
                    {annotator.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="genpanel__field">
            <span>Concept</span>
            <input
              type="text"
              value={concept}
              placeholder={promptStyle === 'phrases' ? 'a bolt. a nut.' : 'a bolt'}
              aria-describedby="concept-hint"
              onChange={(event) => onConceptChange(event.target.value)}
            />
          </label>
          {/* `FieldHint` renders outside the label, which is the rule this used to state
              inline — see doc 39 for why it matters to a screen reader. */}
          <FieldHint id="concept-hint">
            {promptStyle === 'phrases'
              ? 'Grounding DINO finds each phrase and SAM 2.1 turns it into a mask, so several phrases separated by full stops work well. Nothing here is gated — no token, no account.'
              : 'SAM 3 takes one concept at a time — a single noun phrase like “a bolt”. Several phrases in one box are read as one long concept and match poorly; run them one at a time.'}
          </FieldHint>
        </div>
  );
}

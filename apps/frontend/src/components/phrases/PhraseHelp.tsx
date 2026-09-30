/** The three ideas behind phrases, explained where they are used (doc 105). */

import type { JSX } from 'react';

export function PhraseHelp(): JSX.Element {
  return (
    <details className="phrasebar__help">
      <summary>How phrases work</summary>
      <dl>
        <dt>Phrase variations</dt>
        <dd>
          Type the phrase the way you would ask for it, plus 2–4 other wordings, separated by
          commas. The model learns them as one concept. You do not need every synonym: a few
          teach it that the wording can vary, and it generalises from there.
        </dd>
        <dt>All marked · Not in this picture</dt>
        <dd>
          SAM 3 learns from every picture you checked. <em>All marked</em> says every instance
          of this phrase here has an outline. <em>Not in this picture</em> says there is none,
          and teaches the model <em>not</em> to find it here. A picture you did not check is
          left out for that phrase, never guessed.
        </dd>
        <dt>Hard negatives</dt>
        <dd>
          Pictures marked <em>not in this picture</em> are the strongest lessons, especially
          when something similar <em>is</em> there. Add look-alikes as “not to be confused
          with” under Manage phrases. Training also adds generic unrelated phrases (generic
          negatives, <code>num_negatives</code>) and other phrases of your dataset (cross
          negatives, <code>num_cross_negatives</code>) — see SAM 3’s training settings.
        </dd>
      </dl>
    </details>
  );
}

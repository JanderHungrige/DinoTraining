/**
 * A line of guidance under a form field (doc 39).
 *
 * Exists mostly to hold one rule in one place: the hint is rendered **outside** the
 * `<label>`. Text inside a label joins the field's accessible name, so a paragraph there is
 * read out in full every time the field takes focus — a sentence that helps once becomes
 * something a screen-reader user hears on every visit.
 *
 * `aria-describedby` is what actually associates it, which is why the caller passes an id.
 */

import type { JSX, ReactNode } from 'react';

export interface FieldHintProps {
  /** Matches the field's `aria-describedby`. */
  readonly id: string;
  readonly children: ReactNode;
}

export function FieldHint({ id, children }: FieldHintProps): JSX.Element {
  return (
    <p className="fieldhint" id={id}>
      {children}
    </p>
  );
}

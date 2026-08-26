/**
 * One control for "what am I looking at" (doc 67).
 *
 * Three surfaces render model output — the Studio, the Generator and the Inference Viewer
 * — and each answered this differently, none of them completely. The Studio had a
 * checkbox that could not express "boxes only", the other two had nothing at all. Shared
 * rather than repeated so the wording, the order and the keyboard behaviour cannot drift
 * into three dialects of the same question.
 *
 * Renders **nothing** when there is at most one view to offer. A single radio is not a
 * choice, and a box-only result showing a disabled "Segmentation" option invites the
 * reader to wonder what they did wrong.
 */

import type { JSX } from 'react';

import {
  VIEW_LABELS,
  viewsFor,
  type AnnotationView,
} from '../types/annotationView';

export interface AnnotationViewToggleProps {
  readonly view: AnnotationView;
  readonly onChange: (view: AnnotationView) => void;
  readonly hasMasks: boolean;
  readonly hasBoxes: boolean;
  readonly disabled?: boolean;
  /** Distinguishes the radio group when two of these are on one page. */
  readonly groupName?: string;
}

export function AnnotationViewToggle({
  view,
  onChange,
  hasMasks,
  hasBoxes,
  disabled = false,
  groupName = 'annotation-view',
}: AnnotationViewToggleProps): JSX.Element | null {
  const available = viewsFor(hasMasks, hasBoxes);
  if (available.length < 2) return null;

  return (
    <fieldset className="viewtoggle">
      <legend className="viewtoggle__legend">Show</legend>
      {available.map((option) => (
        <label key={option} className="viewtoggle__option">
          <input
            type="radio"
            name={groupName}
            value={option}
            checked={view === option}
            disabled={disabled}
            onChange={() => onChange(option)}
          />
          <span>{VIEW_LABELS[option]}</span>
        </label>
      ))}
    </fieldset>
  );
}

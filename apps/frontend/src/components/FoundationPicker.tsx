/**
 * Pick the foundation detector that will propose boxes (doc 42).
 *
 * Deliberately *not* `ExpertHeadPicker`, for the reason that picker itself gives for not
 * being `HeadRunPanel`: the items are a different type. A head is chosen by backbone
 * compatibility and carries training provenance; a foundation model has neither and is
 * chosen by whether it is installed. Forcing one component to render both would mean a
 * prop for every field only one of them has.
 *
 * What *is* shared is the part that must not drift — the CSS, the three-empty-states rule,
 * and the fact that only a model whose `render_hint` is `boxes` is offered.
 */

import type { JSX } from 'react';

import type { FoundationInfo } from '../api/foundation';

export interface FoundationPickerProps {
  readonly foundations: readonly FoundationInfo[];
  readonly selectedId: string;
  readonly onSelect: (foundationId: string) => void;
  readonly loading?: boolean;
  readonly disabled?: boolean;
  readonly legend?: string;
  readonly groupName?: string;
}

export function FoundationPicker({
  foundations,
  selectedId,
  onSelect,
  loading = false,
  disabled = false,
  legend = 'Detector',
  groupName = 'foundation-model',
}: FoundationPickerProps): JSX.Element {
  // `render_hint`, never `task` — the same authoritative field doc 20 dispatches on. A
  // depth model is a foundation model too, and it cannot be reviewed as boxes.
  const annotatable = foundations.filter((entry) => entry.render_hint === 'boxes');
  const installed = annotatable.filter((entry) => entry.installed);

  if (loading) return <p role="status">Loading detectors…</p>;

  // Three empty states, because the fix differs for each and one message would send the
  // user looking in the wrong place.
  if (annotatable.length === 0) {
    return (
      <p role="status" className="headpick__empty">
        No foundation model in the catalogue proposes boxes.
      </p>
    );
  }

  if (installed.length === 0) {
    return (
      <p role="status" className="headpick__empty">
        {annotatable.length} general detector
        {annotatable.length === 1 ? ' is' : 's are'} available but not downloaded. Get one
        in <strong>Admin / Models</strong> — RF-DETR needs no training and no prompt.
      </p>
    );
  }

  return (
    <fieldset className="headpick">
      <legend>{legend}</legend>
      {installed.map((entry) => (
        <label key={entry.id} className="headpick__option">
          <input
            type="radio"
            name={groupName}
            value={entry.id}
            checked={selectedId === entry.id}
            disabled={disabled}
            onChange={() => onSelect(entry.id)}
          />
          <span className="headpick__name">{entry.title}</span>
          <span className="headpick__meta">
            {entry.description}
            {entry.non_commercial ? ' · non-commercial' : ''}
          </span>
        </label>
      ))}
    </fieldset>
  );
}

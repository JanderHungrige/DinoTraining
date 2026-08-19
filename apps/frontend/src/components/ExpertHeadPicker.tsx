/**
 * Pick the one trained head that will propose boxes.
 *
 * Deliberately *not* `HeadRunPanel`. That panel is a multi-select built for comparison —
 * several heads over one image, several result panes — and the generator wants exactly
 * one head writing into one dataset. Promoting it would have forced compare semantics
 * into a tab with no use for them; copying it would have duplicated the picker. What is
 * shared is the part that must not drift: heads are presented by **`name` + `summary`**,
 * rendered as the backend composed them, never by a filename.
 *
 * Heads are filtered on **`render_hint === 'boxes'`**, the authoritative field, rather
 * than on `task === 'detection'`. Inferring capability from the task is the same defect a
 * `task ===` comparison is in `components/overlays/`.
 */

import { useMemo, type JSX } from 'react';

import { KIND_LABELS, type HeadInstanceInfo } from '../api/headInstances';

export interface ExpertHeadPickerProps {
  readonly heads: readonly HeadInstanceInfo[];
  readonly backboneId: string;
  readonly selectedId: string;
  readonly onSelect: (instanceId: string) => void;
  readonly loading?: boolean;
  readonly disabled?: boolean;
}

export function ExpertHeadPicker({
  heads,
  backboneId,
  selectedId,
  onSelect,
  loading = false,
  disabled = false,
}: ExpertHeadPickerProps): JSX.Element {
  const annotatable = useMemo(
    () => heads.filter((head) => head.render_hint === 'boxes'),
    [heads],
  );
  const compatible = useMemo(
    () => annotatable.filter((head) => head.backbone_id === backboneId),
    [annotatable, backboneId],
  );

  if (loading) return <p role="status">Loading heads…</p>;

  // Three distinct empty states, because the fix differs for each and a single "no heads
  // available" would send the user looking in the wrong place.
  if (annotatable.length === 0) {
    return (
      <p role="status" className="genpanel__empty">
        No installed head can propose boxes. Classification, segmentation and depth heads
        run in the Inference Viewer; only a detection head can be reviewed as boxes — train
        one in the Head Trainer.
      </p>
    );
  }

  if (compatible.length === 0) {
    return (
      <p role="status" className="genpanel__empty">
        {annotatable.length} detection head{annotatable.length === 1 ? '' : 's'} installed,
        but none was trained on <strong>{backboneId}</strong>. Switch backbone, or train a
        head on this one.
      </p>
    );
  }

  return (
    <fieldset className="genpanel__heads">
      <legend>Expert head</legend>
      {compatible.map((head) => (
        <label key={head.id} className="genpanel__head">
          <input
            type="radio"
            name="expert-head"
            value={head.id}
            checked={selectedId === head.id}
            disabled={disabled}
            onChange={() => onSelect(head.id)}
          />
          <span className="genpanel__headname">{head.name}</span>
          <span className="genpanel__headmeta">
            {KIND_LABELS[head.kind]} · {head.summary}
          </span>
        </label>
      ))}
    </fieldset>
  );
}

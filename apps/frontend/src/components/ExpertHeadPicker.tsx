/**
 * Pick the one trained head that will propose boxes.
 *
 * **Shared by the Dataset Generator and the Annotation Studio** (doc 32). Wave 5's plan
 * originally said to promote `HeadRunPanel` instead; that was written before Wave 4 and
 * would have undone this component's founding decision. `HeadRunPanel` is a multi-select
 * built for *comparison* — several heads over one image, several result panes — and both
 * consumers here want exactly **one** head writing into one dataset. Promoting it would
 * force compare semantics into two tabs with no use for them. `HeadRunPanel` therefore
 * stays the Inference Viewer's control, and this stays the picker.
 *
 * What is shared is the part that must not drift: heads are presented by
 * **`name` + `summary`**, rendered as the backend composed them, never by a filename —
 * doc 12's contract, of which this is now the fourth consumer.
 *
 * Heads are filtered on **`render_hint === 'boxes'`**, the authoritative field, rather
 * than on `task === 'detection'`. Inferring capability from the task is the same defect a
 * `task ===` comparison is in `components/overlays/`. It is also what confines the Studio
 * to box heads: a segmentation or depth head has no refine tool there to correct into, and
 * the Studio's promise is hand-refinement.
 *
 * `legend` and `groupName` are props because the two tabs say different things and because
 * two radio groups sharing a `name` on one page would silently deselect each other.
 */

import { useMemo, type JSX } from 'react';

import { describeHead, type HeadInstanceInfo } from '../api/headInstances';
import { useT } from '../i18n';

export interface ExpertHeadPickerProps {
  readonly heads: readonly HeadInstanceInfo[];
  readonly backboneId: string;
  readonly selectedId: string;
  readonly onSelect: (instanceId: string) => void;
  readonly loading?: boolean;
  readonly disabled?: boolean;
  /** Fieldset legend. The Generator picks what proposes; the Studio picks what annotates. */
  readonly legend?: string;
  /** Radio group name. Must differ if two pickers ever share a page. */
  readonly groupName?: string;
}

export function ExpertHeadPicker({
  heads,
  backboneId,
  selectedId,
  onSelect,
  loading = false,
  disabled = false,
  legend,
  groupName = 'expert-head',
}: ExpertHeadPickerProps): JSX.Element {
  const translator = useT();
  const { t, tp } = translator;
  const annotatable = useMemo(
    () => heads.filter((head) => head.render_hint === 'boxes'),
    [heads],
  );
  const compatible = useMemo(
    () => annotatable.filter((head) => head.backbone_id === backboneId),
    [annotatable, backboneId],
  );

  if (loading) return <p role="status">{t('studio.expert.loading')}</p>;

  // Three distinct empty states, because the fix differs for each and a single "no heads
  // available" would send the user looking in the wrong place.
  if (annotatable.length === 0) {
    return (
      <p role="status" className="headpick__empty">
        {t('studio.expert.none')}
      </p>
    );
  }

  if (compatible.length === 0) {
    return (
      <p role="status" className="headpick__empty">
        {tp('studio.expert.incompatible', annotatable.length)} <strong>{backboneId}</strong>
        {t('studio.expert.switch')}
      </p>
    );
  }

  return (
    <fieldset className="headpick">
      <legend>{legend ?? t('studio.expert.legend')}</legend>
      {compatible.map((head) => (
        <label key={head.id} className="headpick__option">
          <input
            type="radio"
            name={groupName}
            value={head.id}
            checked={selectedId === head.id}
            disabled={disabled}
            onChange={() => onSelect(head.id)}
          />
          <span className="headpick__name">{head.name}</span>
          <span className="headpick__meta">{describeHead(head, translator)}</span>
        </label>
      ))}
    </fieldset>
  );
}

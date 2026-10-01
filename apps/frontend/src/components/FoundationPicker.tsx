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

import { proposesBoxes, type FoundationInfo } from '../api/foundation';
import { useT } from '../i18n';
import { describeOutput } from '../types/annotationView';

export interface FoundationPickerProps {
  readonly foundations: readonly FoundationInfo[];
  readonly selectedId: string;
  readonly onSelect: (foundationId: string) => void;
  readonly loading?: boolean;
  readonly disabled?: boolean;
  readonly legend?: string;
  readonly groupName?: string;
  /** Current concept, for a model that needs one. Omit both this and `onConceptChange`
   *  on a surface that has its own prompt field — the Generator already does. */
  readonly concept?: string;
  readonly onConceptChange?: (concept: string) => void;
}

export function FoundationPicker({
  foundations,
  selectedId,
  onSelect,
  loading = false,
  disabled = false,
  legend,
  groupName = 'foundation-model',
  concept,
  onConceptChange,
}: FoundationPickerProps): JSX.Element {
  const { t, tp } = useT();
  // One shared rule, in `foundation.ts`, rather than `render_hint === 'boxes'` inline. A
  // concept segmenter reports `masks` — that is what the *viewer* draws — but Grounding
  // DINO found boxes on the way there, so this surface can review them. Depth cannot be.
  const annotatable = foundations.filter(proposesBoxes);
  const installed = annotatable.filter((entry) => entry.installed);
  const selected = installed.find((entry) => entry.id === selectedId);
  // Only rendered when this surface offered to own the field. The Generator has its own
  // prompt box, and two inputs for one string is how they drift apart.
  const needsConcept = selected?.takes_concept === true && onConceptChange !== undefined;

  if (loading) return <p role="status">{t('studio.foundation.loading')}</p>;

  // Three empty states, because the fix differs for each and one message would send the
  // user looking in the wrong place.
  if (annotatable.length === 0) {
    return (
      <p role="status" className="headpick__empty">
        {t('studio.foundation.none')}
      </p>
    );
  }

  if (installed.length === 0) {
    return (
      <p role="status" className="headpick__empty">
        {tp('studio.foundation.notDownloaded', annotatable.length)}{' '}
        <strong>{t('studio.foundation.adminModels')}</strong> {t('studio.foundation.noTraining')}
      </p>
    );
  }

  return (
    <fieldset className="headpick">
      <legend>{legend ?? t('studio.foundation.legend')}</legend>
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
            {entry.non_commercial ? ` · ${t('studio.foundation.nonCommercial')}` : ''}
          </span>
        </label>
      ))}

      {/* Doc 67. What this model *writes* — stated before the run, which is the only
          point where it can still change the decision. Read off `render_hint`, never off
          an id: Grounded SAM, SAM 3 and a fine-tuned RF-DETR share no id pattern.

          It answers the question behind "boxes, segmentations, or both?": a segmentation
          run gives you boxes too, because the COCO export derives one from each mask. */}
      {selected && describeOutput(selected.render_hint, t) && (
        <p className="genpanel__output">{describeOutput(selected.render_hint, t)}</p>
      )}

      {needsConcept && (
        <label className="headpick__concept">
          <span>{t('studio.foundation.whatToFind')}</span>
          <input
            type="text"
            value={concept ?? ''}
            disabled={disabled}
            placeholder="cat. dog. traffic light."
            onChange={(event) => onConceptChange(event.target.value)}
          />
          <span className="headpick__meta">
            {t('studio.foundation.conceptHint', { model: selected?.title ?? '' })}
          </span>
        </label>
      )}
    </fieldset>
  );
}

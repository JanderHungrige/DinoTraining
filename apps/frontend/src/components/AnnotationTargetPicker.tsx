/**
 * "What will this dataset train?" (doc 104), in the Studio's setup.
 *
 * The list comes from the backend's matrix and the choice is only the user's override
 * (CLAUDE.md): until the list loads, "open" is what is chosen, which is also the default.
 */

import type { JSX } from 'react';

import type { AnnotationTarget } from '../api/annotationTargets';
import { useT } from '../i18n';
import '../targets.css';

export interface AnnotationTargetPickerProps {
  readonly targets: readonly AnnotationTarget[];
  readonly value: string;
  readonly onChange: (target: string) => void;
}

export function AnnotationTargetPicker({ targets, value, onChange }: AnnotationTargetPickerProps): JSX.Element | null {
  const { t } = useT();
  if (targets.length === 0) return null;
  return (
    <fieldset className="setup__modes targetpick">
      <legend>{t('studio.target.legend')}</legend>
      {targets.map((target) => (
        <label key={target.id} className={`targetpick__option${value === target.id ? ' targetpick__option--on' : ''}`}>
          <input
            type="radio"
            name="annotation-target"
            value={target.id}
            checked={value === target.id}
            onChange={() => onChange(target.id)}
          />
          <span>
            <span className="targetpick__name">{target.label}</span> — {target.summary}
          </span>
        </label>
      ))}
    </fieldset>
  );
}

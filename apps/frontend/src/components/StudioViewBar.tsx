/**
 * The Studio's view controls: masks / boxes / both, and hiding what is already there.
 * Split out of the Studio (at the 300-line gate) when doc 106 added the outline tools.
 */

import type { JSX } from 'react';

import { useT } from '../i18n';
import type { AnnotationView } from '../types/annotationView';
import { AnnotationViewToggle } from './AnnotationViewToggle';

export interface StudioViewBarProps {
  readonly view: AnnotationView;
  readonly onView: (view: AnnotationView) => void;
  readonly hasMasks: boolean;
  readonly boxCount: number;
  /** How many are hidden by hand, or null when nothing is. */
  readonly concealed: number | null;
  readonly onToggleConceal: () => void;
  readonly disabled: boolean;
}

export function StudioViewBar(props: StudioViewBarProps): JSX.Element {
  const { boxCount, concealed } = props;
  const { tp } = useT();
  return (
    <div className="studio__viewbar">
      <AnnotationViewToggle
        view={props.view}
        onChange={props.onView}
        hasMasks={props.hasMasks}
        hasBoxes={boxCount > 0}
        disabled={props.disabled}
        groupName="studio-view"
      />

      {/* Hiding what is already there is what makes drawing on a busy image possible:
          thirty proposals cover the thing you wanted to add. Nothing is deleted — hidden
          boxes are still saved, the same rule the slider follows. */}
      {(boxCount > 0 || concealed !== null) && (
        <button type="button" className="btn btn--small" onClick={props.onToggleConceal}>
          {concealed === null
            ? tp('studio.view.hide', boxCount)
            : tp('studio.view.show', concealed)}
        </button>
      )}
    </div>
  );
}

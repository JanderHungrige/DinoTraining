/**
 * A dataset's stored annotations over a frame (doc 74), coloured by **class**, not by
 * verdict: the question here is "what is where", and one colour per class is also what the
 * timeline under the player uses (doc 75), so a bar and a box always agree.
 *
 * Positives only. Inspect shows what the dataset asserts; a rejected proposal is a record
 * of what the model got wrong, and drawing it would read as a detection.
 */

import type { JSX } from 'react';

import type { StoredBox } from '../api/datasets';
import type { Prediction } from '../api/inference';
import type { RenderedImage } from '../lib/geometry';
import { classColour } from '../lib/overlayPalette';
import { showsBoxes, showsMasks, type AnnotationView } from '../types/annotationView';
import type { CanvasBox } from '../types/annotation';
import { BoxOverlay } from './overlays/BoxOverlay';
import { CompositedMasks } from './overlays/CompositedMasks';
import { ENGLISH, useT, type Translator } from '../i18n';

export interface StoredOverlayProps {
  readonly boxes: readonly StoredBox[];
  readonly masks: readonly CanvasBox[];
  /** The dataset's classes, sorted; the index is the colour. */
  readonly classNames: readonly string[];
  readonly width: number;
  readonly height: number;
  readonly rendered: RenderedImage;
  readonly view: AnnotationView;
}

function classIndex(classNames: readonly string[], name: string | null | undefined): number {
  const found = name ? classNames.indexOf(name) : -1;
  return found >= 0 ? found : classNames.length;
}

interface Outline {
  readonly x: number;
  readonly y: number;
  readonly w: number;
  readonly h: number;
  readonly name?: string | null;
  readonly score?: number | null;
}

/** Stored boxes (and mask extents) as the prediction shape `BoxOverlay` already draws. */
export function asPrediction(
  entries: readonly Outline[],
  classNames: readonly string[],
  { t }: Translator = ENGLISH,
): Prediction {
  return {
    instance_id: 'stored',
    head_name: t('run.overlay.stored'),
    head_type_id: 'stored',
    task: 'detection',
    render_hint: 'boxes',
    class_names: [...classNames, t('run.overlay.unnamed')],
    payload: {
      boxes: entries.map((entry) => [entry.x, entry.y, entry.w, entry.h]),
      scores: entries.map((entry) => entry.score ?? 1),
      classes: entries.map((entry) => classIndex(classNames, entry.name)),
    },
    grid: [],
    elapsed_ms: 0,
  };
}

export function StoredOverlay({
  boxes,
  masks,
  classNames,
  width,
  height,
  rendered,
  view,
}: StoredOverlayProps): JSX.Element | null {
  const translator = useT();
  const positiveBoxes = boxes
    .filter((box) => box.label === 'positive')
    .map((box) => ({ ...box, name: box.prompt ?? null }));
  const positiveMasks = masks.filter((mask) => mask.label === 'positive' && mask.mask);
  const outlines = [
    ...positiveBoxes,
    ...(showsBoxes(view)
      ? positiveMasks.map((mask) => ({ ...mask, name: mask.text ?? null }))
      : []),
  ];

  if (outlines.length === 0 && positiveMasks.length === 0) return null;
  return (
    <>
      {showsMasks(view) && positiveMasks.length > 0 && (
        <CompositedMasks
          masks={positiveMasks.map((mask) => ({
            id: mask.id,
            label: mask.label,
            png: mask.mask!.png,
            rgb: classColour(classIndex(classNames, mask.text)),
          }))}
          width={width}
          height={height}
          rendered={rendered}
          selectedId={null}
        />
      )}
      {outlines.length > 0 && (
        <BoxOverlay prediction={asPrediction(outlines, classNames, translator)} rendered={rendered} />
      )}
    </>
  );
}

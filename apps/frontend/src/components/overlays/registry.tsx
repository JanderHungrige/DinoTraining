/**
 * The renderer registry — one entry per `render_hint`, never an `if (task === …)`.
 *
 * This is the frontend half of the discipline the whole of Wave 2 was built on. Adding a
 * head type to the backend registry must render here by adding one entry, without any
 * other file in the UI changing. If a `task` string ever appears in a condition in this
 * folder, that has been broken.
 */

import type { JSX } from 'react';

import type { Prediction, RenderHint } from '../../api/inference';
import type { RenderedImage } from '../../lib/geometry';
import { classColour, depthColour } from '../../lib/overlayPalette';
import { BoxOverlay } from './BoxOverlay';
import { LabelOverlay } from './LabelOverlay';
import { MapOverlay } from './MapOverlay';

export interface OverlayProps {
  readonly prediction: Prediction;
  readonly rendered: RenderedImage;
}

type OverlayRenderer = (props: OverlayProps) => JSX.Element | null;

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' ? value : fallback;
}

const renderMask: OverlayRenderer = ({ prediction, rendered }) => {
  const encoded = prediction.payload['mask_png'];
  if (typeof encoded !== 'string') return null;

  return (
    <MapOverlay
      encoded={encoded}
      width={asNumber(prediction.payload['width'])}
      height={asNumber(prediction.payload['height'])}
      rendered={rendered}
      colourFor={classColour}
      title={`Segmentation from ${prediction.head_name}`}
    />
  );
};

const renderDepth: OverlayRenderer = ({ prediction, rendered }) => {
  const encoded = prediction.payload['depth_png'];
  if (typeof encoded !== 'string') return null;

  return (
    <MapOverlay
      encoded={encoded}
      width={asNumber(prediction.payload['width'])}
      height={asNumber(prediction.payload['height'])}
      rendered={rendered}
      // The payload is already normalised 0..255 across min..max, so the ramp reads it
      // directly; `min`/`max` are for the legend, not for the colouring.
      colourFor={(value) => depthColour(value / 255)}
      opacity={0.85}
      title={`Depth from ${prediction.head_name}`}
    />
  );
};

/**
 * `render_hint` → renderer. The only dispatch in the overlay layer.
 *
 * `Record<RenderHint, …>` rather than a lookup with a default: adding a hint to the union
 * without adding a renderer becomes a compile error rather than a blank result pane.
 */
export const OVERLAY_RENDERERS: Record<RenderHint, OverlayRenderer> = {
  labels: ({ prediction }) => <LabelOverlay prediction={prediction} />,
  boxes: ({ prediction, rendered }) => (
    <BoxOverlay prediction={prediction} rendered={rendered} />
  ),
  masks: renderMask,
  'depth-map': renderDepth,
};

export function renderOverlayFor(
  prediction: Prediction,
  rendered: RenderedImage,
): JSX.Element | null {
  const renderer = OVERLAY_RENDERERS[prediction.render_hint];
  // Unreachable through the type system, but a head type added to the backend and not
  // here would otherwise fail as a blank pane with no explanation.
  if (!renderer) return null;
  return renderer({ prediction, rendered });
}

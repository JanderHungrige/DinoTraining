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
import { classColour, depthColour, type Rgb } from '../../lib/overlayPalette';
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

/**
 * Class 0 is transparent, but only where class 0 means "nothing here".
 *
 * ADE20k's class 0 is `wall` — a real prediction, and dimming it would hide it. A concept
 * segmenter's class 0 is background and it says so by *naming* it, which is the signal
 * used here: nothing branches on which model produced the prediction.
 *
 * Painting a named background opaque is what made Grounded SAM and SAM 3 look broken. At
 * 55% opacity an all-background result is not an empty overlay, it is the whole frame
 * washed in one flat colour — which reads as a nonsense mask rather than as no answer.
 */
const BACKGROUND_CLASS = 'background';

/**
 * A pixel value is the class index **times `class_stride`** — see `encode_class_map`.
 *
 * The stride exists because adjacent class indices make terrible pixel values: with one
 * phrase a concept segmenter's classes are 0 and 1, and a webview that colour-manages the
 * PNG on the way in dithers the low bits, so half the background arrives as the other
 * class. Spread to 0 and 255, it takes a 128-level error to confuse them. Rounding here is
 * what absorbs whatever the conversion did.
 *
 * Absent or zero means 1 — the pre-stride encoding, so an older backend still renders.
 */
function strideOf(payload: Record<string, unknown>): number {
  const stride = asNumber(payload['class_stride'], 1);
  return stride > 0 ? stride : 1;
}

/**
 * Cached per stride, because `MapOverlay` keys its decode effect on these function
 * identities: a fresh closure each render would re-decode the whole PNG every render.
 */
const COLOUR_BY_STRIDE = new Map<number, (value: number) => Rgb>();
const ALPHA_BY_STRIDE = new Map<number, (value: number) => number>();

function colourForStride(stride: number): (value: number) => Rgb {
  const cached = COLOUR_BY_STRIDE.get(stride);
  if (cached) return cached;
  const fn = (value: number): Rgb => classColour(Math.round(value / stride));
  COLOUR_BY_STRIDE.set(stride, fn);
  return fn;
}

/** Background transparent, every real class opaque. */
function alphaForStride(stride: number): (value: number) => number {
  const cached = ALPHA_BY_STRIDE.get(stride);
  if (cached) return cached;
  const fn = (value: number): number => (Math.round(value / stride) > 0 ? 255 : 0);
  ALPHA_BY_STRIDE.set(stride, fn);
  return fn;
}

const renderMask: OverlayRenderer = ({ prediction, rendered }) => {
  const encoded = prediction.payload['mask_png'];
  if (typeof encoded !== 'string') return null;

  const stride = strideOf(prediction.payload);
  const named = prediction.class_names[0] === BACKGROUND_CLASS;

  return (
    <MapOverlay
      encoded={encoded}
      width={asNumber(prediction.payload['width'])}
      height={asNumber(prediction.payload['height'])}
      rendered={rendered}
      colourFor={colourForStride(stride)}
      {...(named ? { alphaFor: alphaForStride(stride) } : {})}
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

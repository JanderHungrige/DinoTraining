/**
 * Dense maps — segmentation masks and depth — drawn to a canvas.
 *
 * One component serves both: the only difference between them is how a pixel value
 * becomes a colour, which arrives as a function. A second near-identical component would
 * be two places to fix the next canvas bug.
 *
 * The payload is a base64 PNG whose pixel values are data, not colour: a class index for
 * a mask, a 0..255 normalised depth for a depth map. Decoding goes through `decodeMap`
 * rather than `drawImage` + `getImageData` directly — read the comment at the top of that
 * file before changing it, because the naive version silently dithers the data and paints
 * a speckle across the whole frame in WebKit.
 */

import { useEffect, useRef, type JSX } from 'react';

import { decodeMap } from '../../lib/decodeMap';
import type { RenderedImage } from '../../lib/geometry';
import type { Rgb } from '../../lib/overlayPalette';

export interface MapOverlayProps {
  /** Base64 PNG (no data: prefix) — one byte per pixel, meaning depends on the caller. */
  readonly encoded: string;
  readonly width: number;
  readonly height: number;
  readonly rendered: RenderedImage;
  /** Pixel value 0..255 → colour. The whole difference between a mask and a depth map. */
  readonly colourFor: (value: number) => Rgb;
  /**
   * Pixel value 0..255 → alpha 0..255. Defaults to fully opaque, which is right for a
   * class-index map where every pixel belongs to some class. A *binary instance* mask is
   * the other case: value 0 means "not this object", and painting it opaque would cover
   * the image with a rectangle instead of showing one shape.
   */
  readonly alphaFor?: (value: number) => number;
  readonly opacity?: number;
  readonly title?: string;
}

export function MapOverlay({
  encoded,
  width,
  height,
  rendered,
  colourFor,
  alphaFor,
  opacity = 0.55,
  title,
}: MapOverlayProps): JSX.Element {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    void decodeMap(encoded, width, height)
      .then((decoded) => {
        // The component may have unmounted, or the prediction changed, while the browser
        // was decoding. Painting then would put one head's mask over another's image.
        if (cancelled || decoded === null) return;
        const canvas = canvasRef.current;
        const context = canvas?.getContext('2d', { colorSpace: 'srgb' });
        if (!canvas || !context) return;

        const image = context.createImageData(width, height);
        const pixels = image.data;
        for (let p = 0, i = 0; p < decoded.values.length; p += 1, i += 4) {
          const value = decoded.values[p] ?? 0;
          const { r, g, b } = colourFor(value);
          pixels[i] = r;
          pixels[i + 1] = g;
          pixels[i + 2] = b;
          pixels[i + 3] = alphaFor ? alphaFor(value) : 255;
        }
        context.putImageData(image, 0, 0);
      })
      .catch(() => {
        // A map that will not decode leaves the pane showing the image alone, which is
        // better than taking the viewer down with it.
      });

    return () => {
      cancelled = true;
    };
  }, [encoded, width, height, colourFor, alphaFor]);

  // Positioned on the *rendered* image rather than the container: an object-fit:contain
  // image is letterboxed, and using the container would offset the whole map.
  return (
    <canvas
      ref={canvasRef}
      className="overlay__map"
      width={width}
      height={height}
      aria-label={title}
      role={title ? 'img' : 'presentation'}
      style={{
        left: `${rendered.offsetX}px`,
        top: `${rendered.offsetY}px`,
        width: `${rendered.width}px`,
        height: `${rendered.height}px`,
        opacity,
      }}
    />
  );
}

/**
 * Dense maps — segmentation masks and depth — drawn to a canvas.
 *
 * One component serves both: the only difference between them is how a pixel value
 * becomes a colour, which arrives as a function. A second near-identical component would
 * be two places to fix the next canvas bug.
 *
 * The payload is a base64 PNG whose pixel values are data, not colour: a class index for
 * a mask, a 0..255 normalised depth for a depth map. So the PNG is decoded to an
 * offscreen canvas, read back, and recoloured — the browser does the decompression and
 * we only pay for the recolour.
 */

import { useEffect, useRef, type JSX } from 'react';

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
    const canvas = canvasRef.current;
    if (!canvas || width <= 0 || height <= 0) return;

    let cancelled = false;
    const image = new Image();

    image.onload = () => {
      // The component may have unmounted, or the prediction changed, while the browser
      // was decoding. Painting then would put one head's mask over another's image.
      if (cancelled) return;

      const source = document.createElement('canvas');
      source.width = width;
      source.height = height;
      const sourceCtx = source.getContext('2d');
      const targetCtx = canvas.getContext('2d');
      if (!sourceCtx || !targetCtx) return;

      sourceCtx.drawImage(image, 0, 0);
      const data = sourceCtx.getImageData(0, 0, width, height);
      const pixels = data.data;

      // The PNG is greyscale, so the red channel carries the value; the rest is repeat.
      // Recolour in place rather than allocating a second buffer — this runs over every
      // pixel of a full-resolution map.
      for (let i = 0; i < pixels.length; i += 4) {
        const value = pixels[i] ?? 0;
        const { r, g, b } = colourFor(value);
        pixels[i] = r;
        pixels[i + 1] = g;
        pixels[i + 2] = b;
        pixels[i + 3] = alphaFor ? alphaFor(value) : 255;
      }

      targetCtx.putImageData(data, 0, 0);
    };

    image.src = `data:image/png;base64,${encoded}`;
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

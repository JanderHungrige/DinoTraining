/**
 * The picture in the player: decode ahead, then paint (doc 68).
 *
 * Extracted from `VideoPlayer` when it crossed the 300-line gate, and the seam is a real
 * one — everything here is about *pixels* (fetching them, holding them, drawing them,
 * measuring where they land) and everything left there is about *controls*.
 *
 * **A canvas painted from a cache, never an `<img>` whose src moves on a clock.** The first
 * version did the latter and playback did not play: a frame was requested only when the
 * clock reached it, the request outlasted the frame interval, and the element never
 * finished decoding before the next src replaced it — so the engine kept showing the last
 * frame that *had* decoded. Measured live: the counter advanced 1,3,5,7,9,11 while
 * `img.complete` was false on every sample.
 *
 * Prefetching alone fixed it in one browser and is still the wrong shape. Whether a
 * half-loaded `<img>` shows the old frame, the new one or nothing is the engine's choice,
 * and this project has been caught by exactly that difference between the dev browser and
 * the packaged WebKit before. `drawImage` is synchronous: what is on screen is the frame
 * that was asked for, or the previous one deliberately held — never whichever the loader
 * happened to finish first.
 */

import { useCallback, useEffect, useRef, useState, type JSX } from 'react';

import { frameUrl } from '../api/video';
import { fitContain, type RenderedImage } from '../lib/geometry';

/**
 * How many frames to decode ahead of the one on screen.
 *
 * Enough to cover a slow frame — a decoded video frame is far slower than a folder's file
 * — without fetching a hundred images the viewer may never reach if they pause.
 */
const PREFETCH_AHEAD = 12;

export interface FrameCanvasProps {
  readonly source: string;
  /** Frame index within the run. */
  readonly index: number;
  /** Where the run starts in the source's own numbering. */
  readonly runStart: number;
  /** How many frames the run covers; 0 before one exists. */
  readonly frames: number;
  readonly naturalWidth: number;
  readonly naturalHeight: number;
  /** Changes when the pixels held are no longer the right ones — a new run, say. */
  readonly generation: string;
  readonly label: string;
  /** Draws over the picture, in the geometry this component measured. */
  readonly renderOverlay: (rendered: RenderedImage) => JSX.Element | null;
}

export function FrameCanvas({
  source,
  index,
  runStart,
  frames,
  naturalWidth,
  naturalHeight,
  generation,
  label,
  renderOverlay,
}: FrameCanvasProps): JSX.Element {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const observerRef = useRef<ResizeObserver | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  //: Decoded frames, by index within the run. Held rather than refetched, so scrubbing
  //: backwards is instant.
  const cache = useRef<Map<number, HTMLImageElement>>(new Map());
  // Bumped when a frame finishes decoding, so the paint effect runs for late arrivals.
  const [decoded, setDecoded] = useState(0);
  const [rendered, setRendered] = useState<RenderedImage>({
    width: 0,
    height: 0,
    offsetX: 0,
    offsetY: 0,
    naturalWidth,
    naturalHeight,
  });

  const measure = useCallback((): void => {
    const node = stageRef.current;
    if (!node) return;
    const box = node.getBoundingClientRect();
    setRendered(fitContain(box.width, box.height, naturalWidth, naturalHeight));
  }, [naturalWidth, naturalHeight]);

  // **A callback ref, not a `useRef` plus an effect.** An effect that reads `ref.current`
  // on mount finds `null` whenever the node appears later, returns early, and never
  // observes — the measurement then stays at 0x0 and every overlay box collapses into the
  // corner. Found exactly that way, live.
  const attachStage = useCallback(
    (node: HTMLDivElement | null): void => {
      observerRef.current?.disconnect();
      stageRef.current = node;
      if (!node) return;
      measure();
      if (typeof ResizeObserver === 'undefined') return;
      const observer = new ResizeObserver(() => measure());
      observer.observe(node);
      observerRef.current = observer;
    },
    [measure],
  );

  useEffect(() => measure(), [measure]);
  useEffect(() => () => observerRef.current?.disconnect(), []);

  // Held pixels are keyed by index *within the run*, so a new run invalidates all of them:
  // its index 0 is a different picture.
  useEffect(() => {
    cache.current = new Map();
    setDecoded(0);
  }, [generation, source]);

  useEffect(() => {
    if (frames === 0) return;
    const wanted = Math.min(PREFETCH_AHEAD, frames - index);
    for (let offset = 0; offset < wanted; offset += 1) {
      const frame = index + offset;
      if (cache.current.has(frame)) continue;
      const image = new Image();
      // **No `crossOrigin`, deliberately.** The sidecar is a different origin, so the
      // canvas ends up tainted and its pixels cannot be read back — which costs nothing,
      // because nothing reads them. Setting it *does* cost: a CORS request for a URL
      // already in the HTTP cache from a non-CORS fetch fails outright, `Vary: Origin`
      // notwithstanding. Measured — every prefetch returned `net::ERR_FAILED` while the
      // same URLs had returned 200 moments earlier, and the canvas stayed blank.
      cache.current.set(frame, image);
      image.onload = () => setDecoded((count) => count + 1);
      image.src = frameUrl(source, runStart + frame);
    }
  }, [index, frames, runStart, source]);

  // Paint the current frame, whenever it or its pixels arrive.
  useEffect(() => {
    const canvas = canvasRef.current;
    const image = cache.current.get(index);
    if (!canvas || !image || !image.complete || image.naturalWidth === 0) return;
    const context = canvas.getContext('2d');
    if (!context) return;
    // Setting either dimension clears the canvas, so this happens immediately before the
    // draw and never on its own.
    canvas.width = image.naturalWidth;
    canvas.height = image.naturalHeight;
    context.drawImage(image, 0, 0);
  }, [index, decoded]);

  return (
    <div className="player__stage" ref={attachStage}>
      <canvas className="player__frame" ref={canvasRef} role="img" aria-label={label} />
      <div className="overlay">{renderOverlay(rendered)}</div>
    </div>
  );
}

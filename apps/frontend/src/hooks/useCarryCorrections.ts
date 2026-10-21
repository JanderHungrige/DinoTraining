/**
 * Carry my corrections to the next picture (doc 170), wired to the Studio's session.
 *
 * Remembers every model proposal as it arrived. When the picture changes, what the user
 * made of those proposals becomes the pending corrections; when the new picture's
 * proposals arrive, the matching ones get the same decision.
 */

import { useEffect, useRef, useState } from 'react';

import { applyCorrections, recordCorrections, type CarryCounts, type Correction } from '../lib/carryCorrections';
import type { CanvasBox } from '../types/annotation';

type Size = { readonly width: number; readonly height: number } | null;

export interface CarrySession {
  readonly currentImage: string | null;
  readonly boxes: readonly CanvasBox[];
  readonly imageSize: Size;
  readonly setBoxes: (boxes: CanvasBox[]) => void;
}

/** A fresh model proposal: not in the dataset, not drawn by hand. */
const isProposal = (box: CanvasBox): boolean => box.saved !== true && box.provenance !== 'hand-drawn';

/** What was carried onto the current picture, for the note; null when nothing was. */
export function useCarryCorrections(session: CarrySession, enabled: boolean): CarryCounts | null {
  const { currentImage, boxes, imageSize, setBoxes } = session;
  const originals = useRef(new Map<string, CanvasBox>());
  const pending = useRef<{ size: Size; corrections: Correction[] } | null>(null);
  const last = useRef<{ image: string | null; boxes: readonly CanvasBox[]; size: Size }>({ image: null, boxes: [], size: null });
  const [carried, setCarried] = useState<CarryCounts | null>(null);

  // Declared first, so it reads the picture being left before `last` moves on.
  useEffect(() => {
    const left = last.current;
    pending.current =
      enabled && left.image !== null && left.image !== currentImage
        ? { size: left.size, corrections: recordCorrections(originals.current, left.boxes) }
        : null;
    originals.current = new Map();
    setCarried(null);
  }, [currentImage]);

  useEffect(() => {
    const fresh = boxes.filter((box) => isProposal(box) && !originals.current.has(box.id));
    if (fresh.length === 0) return;
    for (const box of fresh) originals.current.set(box.id, box);
    const from = pending.current;
    if (!enabled || !from || from.corrections.length === 0 || !sameSize(from.size, imageSize)) return;
    const { boxes: applied, counts } = applyCorrections(fresh, from.corrections);
    if (counts.renamed + counts.verdicts + counts.removed === 0) return;
    const byId = new Map(applied.map((box) => [box.id, box]));
    const freshIds = new Set(fresh.map((box) => box.id));
    setBoxes(boxes.flatMap((box) => (freshIds.has(box.id) ? (byId.has(box.id) ? [byId.get(box.id) as CanvasBox] : []) : [box])));
    setCarried(counts);
  }, [boxes]);

  useEffect(() => {
    last.current = { image: currentImage, boxes, size: imageSize };
  });

  return carried;
}

function sameSize(a: Size, b: Size): boolean {
  return a !== null && b !== null && a.width === b.width && a.height === b.height;
}

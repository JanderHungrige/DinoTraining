/**
 * Editing outlines in the Studio (doc 106): SAM clicks, brush and eraser, undo, and
 * outlines from boxes. Every edit replaces one `CanvasBox`, so it is an ordinary canvas
 * change — unsaved until Save, like a class change.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { outlinesFromBoxes, refineOutline, strokeOutline, type ClickPoint, type EditedMask, type Rect } from '../api/segment';
import { useT } from '../i18n';
import type { CanvasBox } from '../types/annotation';

export type MaskTool = 'none' | 'add' | 'remove' | 'brush' | 'erase';

const UNDO_DEPTH = 20;

export interface MaskEditing {
  readonly tool: MaskTool;
  readonly setTool: (tool: MaskTool) => void;
  readonly radius: number;
  readonly setRadius: (radius: number) => void;
  readonly busy: boolean;
  readonly error: string;
  /** Clicks placed on the selected outline so far. */
  readonly points: readonly ClickPoint[];
  readonly canUndo: boolean;
  readonly undo: () => void;
  readonly click: (x: number, y: number) => void;
  readonly stroke: (path: readonly (readonly [number, number])[]) => void;
  /** Positive boxes on this picture that have no outline yet. */
  readonly unoutlined: number;
  readonly outlineAll: () => void;
}

export function applyEdit(box: CanvasBox, edited: EditedMask): CanvasBox {
  return { ...box, x: edited.x, y: edited.y, w: edited.w, h: edited.h, mask: { rle: edited.rle, png: edited.mask_png } };
}

const rectOf = (box: CanvasBox): Rect => ({ x: box.x, y: box.y, w: box.w, h: box.h });

export function useMaskEditing(
  imagePath: string | null,
  boxes: readonly CanvasBox[],
  setBoxes: (boxes: CanvasBox[]) => void,
  selectedId: string | null,
): MaskEditing {
  const { t } = useT();
  const [tool, setTool] = useState<MaskTool>('none');
  const [radius, setRadius] = useState(8);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  // Clicks belong to one outline, prompted from the box it had when the first click landed.
  const [prompt, setPrompt] = useState<{ id: string; box: Rect; points: ClickPoint[] } | null>(null);
  const history = useRef<{ id: string; before: CanvasBox }[]>([]);
  const [depth, setDepth] = useState(0);
  const latest = useRef(boxes);
  latest.current = boxes;

  useEffect(() => setPrompt(null), [selectedId, imagePath]);
  useEffect(() => {
    history.current = [];
    setDepth(0);
  }, [imagePath]);

  const replace = useCallback(
    (id: string, next: (box: CanvasBox) => CanvasBox) => {
      const before = latest.current.find((box) => box.id === id);
      if (!before) return;
      history.current = [...history.current, { id, before }].slice(-UNDO_DEPTH);
      setDepth(history.current.length);
      setBoxes(latest.current.map((box) => (box.id === id ? next(box) : box)));
    },
    [setBoxes],
  );

  const run = useCallback(async (work: () => Promise<void>) => {
    setBusy(true);
    setError('');
    try {
      await work();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }, []);

  const selected = boxes.find((box) => box.id === selectedId) ?? null;

  const click = useCallback(
    (x: number, y: number) => {
      if (!imagePath || !selected || (tool !== 'add' && tool !== 'remove')) return;
      const base = prompt && prompt.id === selected.id ? prompt : { id: selected.id, box: rectOf(selected), points: [] };
      const next = { ...base, points: [...base.points, { x, y, positive: tool === 'add' }] };
      setPrompt(next);
      void run(async () => {
        const edited = await refineOutline(imagePath, next.box, next.points);
        replace(selected.id, (box) => applyEdit(box, edited));
      });
    },
    [imagePath, selected, tool, prompt, run, replace],
  );

  const stroke = useCallback(
    (path: readonly (readonly [number, number])[]) => {
      if (!selected || path.length === 0 || (tool !== 'brush' && tool !== 'erase')) return;
      if (!selected.mask) {
        setError(t('studio.mask.outlineFirst'));
        return;
      }
      const rle = selected.mask.rle;
      void run(async () => {
        const edited = await strokeOutline(rle, path, radius, tool === 'erase');
        replace(selected.id, (box) => applyEdit(box, edited));
      });
    },
    [selected, tool, radius, run, replace, t],
  );

  const undo = useCallback(() => {
    const last = history.current.pop();
    setDepth(history.current.length);
    if (!last) return;
    setBoxes(latest.current.map((box) => (box.id === last.id ? last.before : box)));
    setPrompt(null);
  }, [setBoxes]);

  const pending = boxes.filter((box) => box.label === 'positive' && box.mask === undefined);
  const outlineAll = useCallback(() => {
    if (!imagePath || pending.length === 0) return;
    const ids = pending.map((box) => box.id);
    void run(async () => {
      const masks = await outlinesFromBoxes(imagePath, pending.map(rectOf));
      const byId = new Map(ids.map((id, i) => [id, masks[i]!]));
      history.current = [...history.current, ...pending.map((box) => ({ id: box.id, before: box }))].slice(-UNDO_DEPTH);
      setDepth(history.current.length);
      setBoxes(latest.current.map((box) => (byId.has(box.id) ? applyEdit(box, byId.get(box.id)!) : box)));
    });
  }, [imagePath, pending, run, setBoxes]);

  return {
    tool,
    setTool,
    radius,
    setRadius,
    busy,
    error,
    points: prompt && prompt.id === selectedId ? prompt.points : [],
    canUndo: depth > 0,
    undo,
    click,
    stroke,
    unoutlined: pending.length,
    outlineAll,
  };
}

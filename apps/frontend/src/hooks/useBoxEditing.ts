/**
 * Every edit the review surface can make to a list of annotations.
 *
 * Extracted from `AnnotationStudioTab` when the conceal toggle pushed that file past the
 * project's 300-line gate. The seam is a real one: these are the operations on the *list*,
 * and what is left in the tab is which of them to wire to which control.
 *
 * All of them are pure list rewrites handed to `setBoxes`, so the session owns dirty state
 * and nothing here has to know that saving exists.
 */

import { useCallback } from 'react';

import type { CanvasBox, Label } from '../types/annotation';

export interface BoxEditing {
  readonly setLabel: (id: string, label: Label) => void;
  readonly rename: (id: string, text: string) => void;
  /** Rename a class on every box in this image carrying it. */
  readonly renameClass: (from: string, to: string) => void;
  readonly remove: (id: string) => void;
  /** Discard exactly the ids given — the score slider's, never a concealed box's. */
  readonly removeAll: (ids: ReadonlySet<string>) => void;
}

export function useBoxEditing(
  boxes: readonly CanvasBox[],
  setBoxes: (boxes: CanvasBox[]) => void,
  onRemoved: (id: string) => void,
): BoxEditing {
  const setLabel = useCallback(
    (id: string, label: Label): void => {
      setBoxes(boxes.map((box) => (box.id === id ? { ...box, label } : box)));
    },
    [boxes, setBoxes],
  );

  const rename = useCallback(
    (id: string, text: string): void => {
      setBoxes(boxes.map((box) => (box.id === id ? { ...box, text } : box)));
    },
    [boxes, setBoxes],
  );

  /**
   * Rename a class on **every box in this image** that carries it (doc 60).
   *
   * The scope is the image, not the session, and that is the honest boundary: only the
   * current image is saved on navigate, so rewriting the others would edit pictures that
   * are not on screen and persist none of them.
   *
   * A local edit like any other — it marks the session dirty and goes out with the next
   * save. It deliberately does not call the classes API: the new name reaches the table by
   * riding on a saved box, and the old one stays in the vocabulary until it is deleted.
   */
  const renameClass = useCallback(
    (from: string, to: string): void => {
      const target = to.trim();
      if (target === '' || target === from) return;
      setBoxes(boxes.map((box) => (box.text === from ? { ...box, text: target } : box)));
    },
    [boxes, setBoxes],
  );

  const remove = useCallback(
    (id: string): void => {
      setBoxes(boxes.filter((box) => box.id !== id));
      onRemoved(id);
    },
    [boxes, setBoxes, onRemoved],
  );

  const removeAll = useCallback(
    (ids: ReadonlySet<string>): void => {
      setBoxes(boxes.filter((box) => !ids.has(box.id)));
    },
    [boxes, setBoxes],
  );

  return { setLabel, rename, renameClass, remove, removeAll };
}

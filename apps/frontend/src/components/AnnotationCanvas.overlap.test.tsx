/**
 * Overlapping boxes on the canvas (doc 47).
 *
 * Split from `AnnotationCanvas.test.tsx` for the 300-line rule, and the seam is honest:
 * everything there is about drawing, labelling and keyboard operation, everything here is
 * about the bug Jan reported — a box covered by a larger one could not be clicked.
 */

import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { numbered } from '../lib/boxReview';
import type { CanvasBox } from '../types/annotation';
import { AnnotationCanvas } from './AnnotationCanvas';

const BOX: CanvasBox = {
  id: 'b1',
  label: 'positive',
  provenance: 'grounding-dino',
  x: 10,
  y: 20,
  w: 40,
  h: 30,
  score: 0.87,
  text: 'a cat',
};

beforeEach(() => {
  // The canvas measures itself to place boxes; jsdom reports a zero-size element.
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    x: 0,
    y: 0,
    width: 400,
    height: 200,
    top: 0,
    left: 0,
    right: 400,
    bottom: 200,
    toJSON: () => ({}),
  } as DOMRect);
});

function renderCanvas(
  boxes: readonly CanvasBox[] = [BOX],
  selectedId: string | null = null,
  hidden: ReadonlySet<string> = new Set(),
) {
  render(
    <AnnotationCanvas
      imageUrl="/img.png"
      naturalWidth={200}
      naturalHeight={100}
      boxes={numbered(boxes)}
      selectedId={selectedId}
      hidden={hidden}
      onBoxesChange={vi.fn()}
      onSelect={vi.fn()}
    />,
  );
}

describe('overlapping boxes (doc 47)', () => {
  /** A small box entirely inside a large one — the case Jan reported as unclickable. */
  const COVERED = [
    { ...BOX, id: 'big', w: 400, h: 400, text: 'room' },
    { ...BOX, id: 'small', x: 20, y: 20, w: 20, h: 20, text: 'cup' },
  ];

  it('paints the covering box first so the covered one is on top', () => {
    // Every box is a button filling its own rect, so whichever is painted last takes the
    // click. Before this, the large box swallowed every click meant for the small one.
    renderCanvas(COVERED);
    const order = screen.getAllByRole('button').map((b) => b.getAttribute('aria-label'));
    expect(order[0]).toMatch(/room/);
    expect(order[1]).toMatch(/cup/);
  });

  it("keeps each box number from the unfiltered list, not the paint order", () => {
    renderCanvas(COVERED);
    // 'room' is first in the list and so is box 1, even though it is painted first.
    expect(screen.getByRole('button', { name: /room/ })).toHaveAccessibleName(/Box 1/);
    expect(screen.getByRole('button', { name: /cup/ })).toHaveAccessibleName(/Box 2/);
  });

  it('shows the class on the box rather than the verdict', () => {
    // For detection output the class is what is being checked; the verdict is legible
    // from the colour, and the number is how the box is named in the list beside it.
    renderCanvas(COVERED);
    expect(screen.getByText('cup')).toBeInTheDocument();
  });

  it('does not draw a box the threshold is hiding', () => {
    renderCanvas(COVERED, null, new Set(['small']));
    expect(screen.queryByRole('button', { name: /cup/ })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: /room/ })).toBeInTheDocument();
  });
});

import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CanvasBox } from '../types/annotation';
import { numbered } from '../lib/boxReview';
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
  // jsdom has no layout: every getBoundingClientRect is 0x0, so the canvas would
  // measure nothing and place every box at the origin. Pin a 200x100 stage.
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    x: 0,
    y: 0,
    width: 200,
    height: 100,
    top: 0,
    left: 0,
    right: 200,
    bottom: 100,
    toJSON: () => ({}),
  } as DOMRect);
});

function renderCanvas(
  boxes: readonly CanvasBox[] = [BOX],
  selectedId: string | null = null,
  hidden: ReadonlySet<string> = new Set(),
) {
  const onBoxesChange = vi.fn<(boxes: CanvasBox[]) => void>();
  const onSelect = vi.fn<(id: string | null) => void>();
  render(
    <AnnotationCanvas
      imageUrl="/img.png"
      naturalWidth={200}
      naturalHeight={100}
      boxes={numbered(boxes)}
      selectedId={selectedId}
      hidden={hidden}
      onBoxesChange={onBoxesChange}
      onSelect={onSelect}
    />,
  );
  return { onBoxesChange, onSelect };
}

describe('AnnotationCanvas rendering', () => {
  it('renders each box as a focusable button', () => {
    renderCanvas();
    const boxes = screen.getAllByRole('button');
    expect(boxes).toHaveLength(1);
    expect(boxes[0]?.tagName).toBe('BUTTON');
  });

  it('gives each box an accessible name carrying label, text and score', () => {
    renderCanvas();
    const box = screen.getByRole('button');
    expect(box).toHaveAccessibleName(/positive/i);
    expect(box).toHaveAccessibleName(/a cat/i);
    expect(box).toHaveAccessibleName(/87%/);
  });

  it('documents its shortcuts in the accessible name', () => {
    renderCanvas();
    expect(screen.getByRole('button')).toHaveAccessibleName(/press 1, 2 or 3/i);
  });

  it('marks the selected box as pressed', () => {
    renderCanvas([BOX], 'b1');
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  });

  it('renders an empty overlay without boxes', () => {
    renderCanvas([]);
    expect(screen.queryAllByRole('button')).toHaveLength(0);
  });

  it('gives the image an empty alt — the boxes carry the meaning', () => {
    renderCanvas();
    // Decorative: the annotations are the content, and a filename alt would be noise.
    expect(document.querySelector('img')).toHaveAttribute('alt', '');
  });
});

describe('labelling', () => {
  it('cycles positive to negative on click', async () => {
    const user = userEvent.setup();
    const { onBoxesChange } = renderCanvas();

    await user.click(screen.getByRole('button'));

    expect(onBoxesChange).toHaveBeenCalledOnce();
    expect(onBoxesChange.mock.calls[0]?.[0][0]?.label).toBe('negative');
  });

  it('cycles negative to unclear', async () => {
    const user = userEvent.setup();
    const { onBoxesChange } = renderCanvas([{ ...BOX, label: 'negative' }]);

    await user.click(screen.getByRole('button'));

    expect(onBoxesChange.mock.calls[0]?.[0][0]?.label).toBe('unclear');
  });

  it('wraps unclear back to positive', async () => {
    const user = userEvent.setup();
    const { onBoxesChange } = renderCanvas([{ ...BOX, label: 'unclear' }]);

    await user.click(screen.getByRole('button'));

    expect(onBoxesChange.mock.calls[0]?.[0][0]?.label).toBe('positive');
  });

  it.each([
    ['1', 'positive'],
    ['2', 'negative'],
    ['3', 'unclear'],
    ['p', 'positive'],
    ['n', 'negative'],
    ['u', 'unclear'],
  ])('sets the label with the %s key', async (key, expected) => {
    const user = userEvent.setup();
    const { onBoxesChange } = renderCanvas([{ ...BOX, label: 'unclear' }]);

    screen.getByRole('button').focus();
    await user.keyboard(key);

    expect(onBoxesChange.mock.calls.at(-1)?.[0][0]?.label).toBe(expected);
  });

  it('does not mutate the input array', async () => {
    const user = userEvent.setup();
    const boxes = [BOX];
    const { onBoxesChange } = renderCanvas(boxes);

    await user.click(screen.getByRole('button'));

    expect(boxes[0]?.label).toBe('positive');
    expect(onBoxesChange.mock.calls[0]?.[0]).not.toBe(boxes);
  });

  it('only relabels the box that was acted on', async () => {
    const user = userEvent.setup();
    const second: CanvasBox = { ...BOX, id: 'b2', label: 'unclear' };
    const { onBoxesChange } = renderCanvas([BOX, second]);

    await user.click(screen.getAllByRole('button')[0]!);

    const emitted = onBoxesChange.mock.calls[0]?.[0];
    expect(emitted?.[1]?.label).toBe('unclear');
  });
});

describe('removal and selection', () => {
  it('removes the focused box on Delete', async () => {
    const user = userEvent.setup();
    const { onBoxesChange, onSelect } = renderCanvas();

    screen.getByRole('button').focus();
    await user.keyboard('{Delete}');

    expect(onBoxesChange.mock.calls.at(-1)?.[0]).toEqual([]);
    expect(onSelect).toHaveBeenLastCalledWith(null);
  });

  it('removes on Backspace too', async () => {
    const user = userEvent.setup();
    const { onBoxesChange } = renderCanvas();

    screen.getByRole('button').focus();
    await user.keyboard('{Backspace}');

    expect(onBoxesChange.mock.calls.at(-1)?.[0]).toEqual([]);
  });

  it('deselects on Escape', async () => {
    const user = userEvent.setup();
    const { onSelect } = renderCanvas([BOX], 'b1');

    screen.getByRole('button').focus();
    await user.keyboard('{Escape}');

    expect(onSelect).toHaveBeenLastCalledWith(null);
  });

  it('selects a box when it receives focus', () => {
    const { onSelect } = renderCanvas();
    screen.getByRole('button').focus();
    expect(onSelect).toHaveBeenCalledWith('b1');
  });

  it('ignores unrelated keys', async () => {
    const user = userEvent.setup();
    const { onBoxesChange } = renderCanvas();

    screen.getByRole('button').focus();
    await user.keyboard('xyz');

    expect(onBoxesChange).not.toHaveBeenCalled();
  });
});

describe('drawing', () => {
  function stage(): HTMLElement {
    return screen.getByTestId('canvas-stage');
  }

  function drag(element: HTMLElement, from: [number, number], to: [number, number]): void {
    element.setPointerCapture = vi.fn();
    element.releasePointerCapture = vi.fn();
    const opts = { pointerId: 1, isPrimary: true };
    fireEvent.pointerDown(element, { ...opts, clientX: from[0], clientY: from[1], button: 0 });
    fireEvent.pointerMove(element, { ...opts, clientX: to[0], clientY: to[1] });
    fireEvent.pointerUp(element, { ...opts, clientX: to[0], clientY: to[1] });
  }

  it('creates a hand-drawn positive box from a drag', () => {
    const { onBoxesChange } = renderCanvas([]);

    drag(stage(), [20, 20], [80, 60]);

    const created = onBoxesChange.mock.calls.at(-1)?.[0].at(-1);
    expect(created?.provenance).toBe('hand-drawn');
    expect(created?.label).toBe('positive');
    expect(created?.w).toBeGreaterThan(0);
    expect(created?.h).toBeGreaterThan(0);
  });

  it('keeps existing boxes when adding a new one', () => {
    const { onBoxesChange } = renderCanvas([BOX]);

    drag(stage(), [20, 20], [80, 60]);

    expect(onBoxesChange.mock.calls.at(-1)?.[0]).toHaveLength(2);
  });

  it('discards a stray click instead of storing a degenerate box', () => {
    const { onBoxesChange, onSelect } = renderCanvas([]);

    drag(stage(), [30, 30], [32, 31]);

    expect(onBoxesChange).not.toHaveBeenCalled();
    expect(onSelect).toHaveBeenLastCalledWith(null);
  });

  it('clamps a drag that runs past the image edge', () => {
    const { onBoxesChange } = renderCanvas([]);

    drag(stage(), [50, 20], [400, 300]);

    const created = onBoxesChange.mock.calls.at(-1)?.[0].at(-1);
    expect((created?.x ?? 0) + (created?.w ?? 0)).toBeLessThanOrEqual(200);
    expect((created?.y ?? 0) + (created?.h ?? 0)).toBeLessThanOrEqual(100);
  });

  it('selects the newly drawn box', () => {
    const { onBoxesChange, onSelect } = renderCanvas([]);

    drag(stage(), [20, 20], [80, 60]);

    const created = onBoxesChange.mock.calls.at(-1)?.[0].at(-1);
    expect(onSelect).toHaveBeenLastCalledWith(created?.id);
  });

  /**
   * The bug every other test in this block missed.
   *
   * They all press on the stage, where `event.target` is the stage. In a browser it never
   * is: the image fills the stage, so the press lands on the *image* and bubbles up. The
   * old guard asked for `target === currentTarget` and rejected exactly that, which meant
   * drawing a box by hand was impossible in the running app while every test passed.
   *
   * jsdom cannot resolve `pointer-events: none`, so the CSS half of the fix is invisible
   * here — which is why the guard itself has to be right, and why this presses on the
   * image rather than the stage.
   */
  function image(): HTMLElement {
    const node = document.querySelector('.canvas__image');
    if (!(node instanceof HTMLElement)) throw new Error('no canvas image');
    return node;
  }

  it('draws when the press lands on the image, as it does in a browser', () => {
    const { onBoxesChange } = renderCanvas([]);

    drag(image(), [20, 20], [80, 60]);

    const created = onBoxesChange.mock.calls.at(-1)?.[0].at(-1);
    expect(created?.provenance).toBe('hand-drawn');
    expect(created?.w).toBeGreaterThan(0);
    expect(created?.h).toBeGreaterThan(0);
  });

  it('still treats a press on a box as that box\u2019s click, not a new drag', () => {
    const { onBoxesChange } = renderCanvas([BOX]);

    drag(screen.getByRole('button'), [12, 22], [70, 55]);

    // The click cycles the label; what must not happen is a second box appearing.
    for (const call of onBoxesChange.mock.calls) {
      expect(call[0]).toHaveLength(1);
    }
  });
});

describe('the annotation view (doc 67)', () => {
  /**
   * Replaced a `showBoxes` boolean that had no test at all. The boolean could say "mask"
   * and "mask + box" and never "box alone" — the view for checking a mask's extents
   * against a detector's, and the one state that did not exist.
   *
   * A segmented annotation keeps its button under every view: mask pixels cannot be
   * focused, and every keyboard affordance here hangs off that button. So what changes is
   * whether the rect is *painted*, which is `canvas__box--bare`.
   */
  const SEGMENTED: CanvasBox = {
    ...BOX,
    id: 'm1',
    // `size` is COCO's [height, width]; `counts` alternates background/foreground runs.
    mask: { rle: { size: [100, 200], counts: [0, 20_000] }, png: '' },
  };

  function renderWithView(view: 'masks' | 'boxes' | 'both', boxes = [SEGMENTED]) {
    const { container } = render(
      <AnnotationCanvas
        imageUrl="/img.png"
        naturalWidth={200}
        naturalHeight={100}
        boxes={numbered(boxes)}
        selectedId={null}
        hidden={new Set()}
        onBoxesChange={vi.fn()}
        onSelect={vi.fn()}
        view={view}
      />,
    );
    return container;
  }

  it('paints the mask and hides the rect under "masks"', () => {
    const container = renderWithView('masks');

    expect(container.querySelector('.masklayer, canvas')).toBeTruthy();
    expect(container.querySelector('.canvas__box--bare')).toBeTruthy();
  });

  it('paints the rect and drops the mask under "boxes"', () => {
    // The state the old boolean could not reach.
    const container = renderWithView('boxes');

    expect(container.querySelector('.masklayer, canvas')).toBeNull();
    expect(container.querySelector('.canvas__box--bare')).toBeNull();
  });

  it('paints both under "both"', () => {
    const container = renderWithView('both');

    expect(container.querySelector('.masklayer, canvas')).toBeTruthy();
    expect(container.querySelector('.canvas__box--bare')).toBeNull();
  });

  it('keeps the button focusable under every view', () => {
    // Removing it would take the verdict keys and the accessibility tree with it.
    for (const view of ['masks', 'boxes', 'both'] as const) {
      const container = renderWithView(view);
      expect(container.querySelector('button')).toBeTruthy();
    }
  });

  it('always draws a box that has no mask', () => {
    // Nothing else of it exists to draw. Under "masks" it must not vanish.
    const container = renderWithView('masks', [BOX]);

    expect(container.querySelector('.canvas__box--bare')).toBeNull();
    expect(container.querySelector('.canvas__box')).toBeTruthy();
  });
});

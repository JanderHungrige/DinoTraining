import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ReviewMask } from '../types/annotation';
import { MaskReviewCanvas } from './MaskReviewCanvas';

// A 1x1 transparent PNG. The canvas work is exercised in MapOverlay's own tests; here the
// concern is the review controls, and jsdom decodes no images anyway.
const PNG =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

function mask(overrides: Partial<ReviewMask> = {}): ReviewMask {
  return {
    id: 'm1',
    label: 'positive',
    provenance: 'grounded-sam',
    maskPng: PNG,
    x: 10,
    y: 20,
    w: 100,
    h: 50,
    score: 0.82,
    concept: 'a bolt',
    ...overrides,
  };
}

/**
 * jsdom reports every element as 0x0, so geometry computed from the wrong box behaves
 * exactly like geometry computed from the right one — both produce zero. The stub must be
 * installed BEFORE mount, because measurement runs in a mount effect.
 */
function stubStageSize(width = 400, height = 300): void {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({
    width,
    height,
    top: 0,
    left: 0,
    right: width,
    bottom: height,
    x: 0,
    y: 0,
    toJSON: () => ({}),
  } as DOMRect);
}

function renderCanvas(masks: readonly ReviewMask[], props: Record<string, unknown> = {}) {
  const onMasksChange = vi.fn();
  const onSelect = vi.fn();
  render(
    <MaskReviewCanvas
      imageUrl="/img.png"
      naturalWidth={400}
      naturalHeight={300}
      masks={masks}
      selectedId={null}
      onMasksChange={onMasksChange}
      onSelect={onSelect}
      {...props}
    />,
  );
  return { onMasksChange, onSelect };
}

beforeEach(() => stubStageSize());
afterEach(() => vi.restoreAllMocks());

describe('MaskReviewCanvas', () => {
  it('gives every mask a focusable control', () => {
    renderCanvas([mask(), mask({ id: 'm2', concept: 'a nut' })]);
    expect(screen.getAllByRole('button')).toHaveLength(2);
  });

  it('names the mask by its verdict, concept and score', () => {
    renderCanvas([mask()]);
    expect(
      screen.getByRole('button', { name: /Positive mask: a bolt, 82%/ }),
    ).toBeInTheDocument();
  });

  it('cycles the verdict on click', async () => {
    const user = userEvent.setup();
    const { onMasksChange } = renderCanvas([mask()]);

    await user.click(screen.getByRole('button'));

    expect(onMasksChange).toHaveBeenCalledWith([expect.objectContaining({ label: 'negative' })]);
  });

  it('sets a verdict directly with 1, 2 and 3', async () => {
    const user = userEvent.setup();
    const { onMasksChange } = renderCanvas([mask({ label: 'positive' })]);

    screen.getByRole('button').focus();
    await user.keyboard('3');

    expect(onMasksChange).toHaveBeenCalledWith([expect.objectContaining({ label: 'unclear' })]);
  });

  it('changes only the mask that was acted on', async () => {
    const user = userEvent.setup();
    const { onMasksChange } = renderCanvas([mask(), mask({ id: 'm2', concept: 'a nut' })]);

    await user.click(screen.getAllByRole('button')[1]!);

    const next = onMasksChange.mock.calls[0]?.[0] as ReviewMask[];
    expect(next[0]?.label).toBe('positive');
    expect(next[1]?.label).toBe('negative');
  });

  it('does not delete a rejected mask', async () => {
    // A negative mask is information the trainer can use; removing it throws that away.
    const user = userEvent.setup();
    const { onMasksChange } = renderCanvas([mask({ label: 'negative' })]);

    screen.getByRole('button').focus();
    await user.keyboard('{Delete}');

    expect(onMasksChange).not.toHaveBeenCalled();
  });

  it('reports selection on focus', async () => {
    const user = userEvent.setup();
    const { onSelect } = renderCanvas([mask()]);

    await user.tab();
    expect(onSelect).toHaveBeenCalledWith('m1');
  });

  it('places the hit target on the mask bounding box, scaled to the render', () => {
    // 400x300 natural into a 400x300 stage is 1:1, so the box lands at its own numbers.
    // The exact values matter: a loose assertion passes at 0 too, which is what jsdom
    // reports for everything by default.
    renderCanvas([mask({ x: 10, y: 20, w: 100, h: 50 })]);

    const style = screen.getByRole('button').style;
    expect(style.left).toBe('10px');
    expect(style.top).toBe('20px');
    expect(style.width).toBe('100px');
    expect(style.height).toBe('50px');
  });

  it('scales and offsets the hit target when the image is letterboxed', () => {
    vi.restoreAllMocks();
    stubStageSize(400, 400); // a 4:3 image in a square stage letterboxes vertically

    renderCanvas([mask({ x: 0, y: 0, w: 400, h: 300 })]);

    const style = screen.getByRole('button').style;
    expect(style.width).toBe('400px');
    expect(style.height).toBe('300px');
    // (400 - 300) / 2 — the letterbox, which a container-based measurement would miss.
    expect(style.top).toBe('50px');
  });

  it('marks the selected mask', () => {
    renderCanvas([mask()], { selectedId: 'm1' });
    expect(screen.getByRole('button')).toHaveAttribute('aria-pressed', 'true');
  });

  it('renders nothing to review when there are no masks', () => {
    renderCanvas([]);
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('cannot be reviewed while disabled', () => {
    renderCanvas([mask()], { disabled: true });
    expect(screen.getByRole('button')).toBeDisabled();
  });
});

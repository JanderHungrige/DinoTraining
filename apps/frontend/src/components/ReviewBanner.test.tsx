import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Review } from '../hooks/useReview';
import type { CanvasBox } from '../types/annotation';
import { ReviewBanner } from './ReviewBanner';

const review = (overrides: Partial<Review> = {}): Review => ({
  className: 'm10', total: 20, error: '', start: vi.fn(), end: vi.fn(), notHere: vi.fn(async () => undefined), ...overrides,
});
const M10: CanvasBox = { id: 'b', label: 'positive', provenance: 'hand-drawn', x: 0, y: 0, w: 1, h: 1, text: 'm10' };

describe('ReviewBanner (doc 119)', () => {
  it('says which picture of how many, and offers "No m10 here" and End', async () => {
    const user = userEvent.setup();
    const state = review();
    render(<ReviewBanner review={state} position={3} boxes={[]} busy={false} />);
    expect(screen.getByText('Reviewing for m10 — picture 3 of 20.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'No m10 here →' }));
    expect(state.notHere).toHaveBeenCalled();
    await user.click(screen.getByRole('button', { name: 'End review' }));
    expect(state.end).toHaveBeenCalled();
  });

  it('cannot say "no m10" on a picture that has one', () => {
    render(<ReviewBanner review={review()} position={1} boxes={[M10]} busy={false} />);
    expect(screen.getByRole('button', { name: 'No m10 here →' })).toBeDisabled();
  });

  it('shows nothing outside a review', () => {
    const { container } = render(<ReviewBanner review={review({ className: null })} position={1} boxes={[]} busy={false} />);
    expect(container).toBeEmptyDOMElement();
  });
});

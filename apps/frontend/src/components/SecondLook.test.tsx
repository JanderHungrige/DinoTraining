import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { SecondLook as State } from '../hooks/useSecondLook';
import { SecondLook, figure } from './SecondLook';

function look(overrides: Partial<State> = {}): State {
  return { info: null, active: false, error: '', start: vi.fn(), stop: vi.fn(), judge: vi.fn(), ...overrides };
}
const INFO = { sample: ['/a.png', '/b.png'], verdicts: { '/a.png': 'changed' as const }, reviewed: 1, changed: 1, rate: 1 };

describe('SecondLook (doc 109)', () => {
  it('reads the figure as a share of what was judged', () => {
    expect(figure(2, 12, 2 / 12)).toBe('2 of 12 needed a change (17 %)');
    expect(figure(0, 0, null)).toBe('Nothing judged yet.');
  });

  it('starts a sample', async () => {
    const user = userEvent.setup();
    const state = look();
    render(<SecondLook look={state} currentImage="/a.png" disabled={false} />);
    await user.click(screen.getByRole('button', { name: 'Second look' }));
    expect(state.start).toHaveBeenCalled();
  });

  it('judges a sampled picture and shows the verdict already given', async () => {
    const user = userEvent.setup();
    const state = look({ active: true, info: INFO });
    render(<SecondLook look={state} currentImage="/a.png" disabled={false} />);
    expect(screen.getByRole('button', { name: 'Needed a change' })).toHaveClass('secondlook__on');
    await user.click(screen.getByRole('button', { name: 'Looks right' }));
    expect(state.judge).toHaveBeenCalledWith('/a.png', 'right');
    expect(screen.getByText(/1 of 2 judged · 1 of 1 needed a change \(100 %\)/)).toBeInTheDocument();
  });

  it('offers no verdict on a picture outside the sample', () => {
    render(<SecondLook look={look({ active: true, info: INFO })} currentImage="/other.png" disabled={false} />);
    expect(screen.queryByRole('button', { name: 'Looks right' })).toBeNull();
  });
});

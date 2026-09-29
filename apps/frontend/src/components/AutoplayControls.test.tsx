import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { Autoplay } from '../hooks/useAutoplay';
import { AutoplayControls } from './AutoplayControls';
import { AutoplayBar, AutoplaySummary, percentOf } from './AutoplayProgress';

function autoplay(overrides: Partial<Autoplay> = {}): Autoplay {
  return {
    running: false,
    hidden: false,
    setHidden: vi.fn(),
    progress: null,
    report: null,
    play: vi.fn(),
    stop: vi.fn(),
    ...overrides,
  };
}

const PROGRESS = { done: 34, total: 100, saved: 20, empty: 12, failed: 2, skipped: 0 };

describe('AutoplayControls (doc 71)', () => {
  it('offers Play when idle, and starts the run', async () => {
    const user = userEvent.setup();
    const state = autoplay();
    render(<AutoplayControls autoplay={state} canPlay />);
    await user.click(screen.getByRole('button', { name: /play/i }));
    expect(state.play).toHaveBeenCalled();
  });

  it('turns into a Stop that works while everything else is locked', async () => {
    const user = userEvent.setup();
    const state = autoplay({ running: true, progress: PROGRESS });
    render(<AutoplayControls autoplay={state} canPlay={false} />);
    const stop = screen.getByRole('button', { name: /stop/i });
    expect(stop).toBeEnabled();
    await user.click(stop);
    expect(state.stop).toHaveBeenCalled();
    expect(screen.getByRole('status')).toHaveTextContent('34 / 100');
  });

  it('does not let the hidden choice change mid-run', () => {
    render(<AutoplayControls autoplay={autoplay({ running: true })} canPlay={false} />);
    expect(screen.getByRole('checkbox', { name: /run hidden/i })).toBeDisabled();
  });

  it('cannot play when there is nothing to play', () => {
    render(<AutoplayControls autoplay={autoplay()} canPlay={false} />);
    expect(screen.getByRole('button', { name: /play/i })).toBeDisabled();
  });
});

describe('AutoplayBar and AutoplaySummary', () => {
  it('shows a percentage and what happened so far', () => {
    render(<AutoplayBar progress={PROGRESS} />);
    expect(screen.getByText('34 %')).toBeInTheDocument();
    expect(screen.getByRole('progressbar', { name: /34 percent/i })).toHaveAttribute('value', '34');
    expect(screen.getByText(/20 saved · 12 with nothing found · 2 failed/)).toBeInTheDocument();
  });

  it('calls an empty run complete rather than dividing by zero', () => {
    expect(percentOf({ ...PROGRESS, done: 0, total: 0 })).toBe(100);
  });

  it('says why a run ended, with the last failure', () => {
    render(
      <AutoplaySummary
        report={{ ...PROGRESS, end: 'save-failed', lastIndex: 3, lastError: 'model missing' }}
      />,
    );
    expect(screen.getByRole('status')).toHaveTextContent(/could not be saved/);
    expect(screen.getByRole('status')).toHaveTextContent(/Last failure: model missing/);
  });
});

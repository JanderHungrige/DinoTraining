import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { DatasetCounts } from '../api/datasets';
import { CounterBar } from './CounterBar';

const COUNTS: DatasetCounts = {
  images: 7,
  boxes: 12,
  masks: 0,
  positive: 8,
  negative: 3,
  unclear: 1,
};

function renderBar(overrides: Partial<Parameters<typeof CounterBar>[0]> = {}) {
  render(
    <CounterBar counts={COUNTS} imageIndex={2} imageTotal={10} dirty={false} {...overrides} />,
  );
}

describe('CounterBar', () => {
  it('announces itself as a live status region', () => {
    renderBar();
    const status = screen.getByRole('status');
    expect(status).toHaveAttribute('aria-live', 'polite');
  });

  it('shows a one-based image position', () => {
    renderBar();
    // Index 2 is the third image; showing "2 / 10" would be off by one to a human.
    expect(screen.getByRole('status')).toHaveTextContent('3 / 10');
  });

  it('shows zero rather than one for an empty folder', () => {
    renderBar({ imageIndex: 0, imageTotal: 0 });
    expect(screen.getByRole('status')).toHaveTextContent('0 / 0');
  });

  it('renders each label count', () => {
    renderBar();
    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('Positive 8');
    expect(status).toHaveTextContent('Negative 3');
    expect(status).toHaveTextContent('Unclear 1');
  });

  it('shows the saved image count from the backend', () => {
    renderBar();
    expect(screen.getByRole('status')).toHaveTextContent('Saved images 7');
  });

  it('flags unsaved changes only when dirty', () => {
    renderBar({ dirty: true });
    expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument();
  });

  it('hides the unsaved flag when clean', () => {
    renderBar({ dirty: false });
    expect(screen.queryByText(/unsaved changes/i)).not.toBeInTheDocument();
  });
});

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { MaskEditing } from '../hooks/useMaskEditing';
import { MaskEditBar } from './MaskEditBar';

function editing(overrides: Partial<MaskEditing> = {}): MaskEditing {
  return {
    tool: 'none', setTool: vi.fn(), radius: 8, setRadius: vi.fn(), busy: false, error: '', points: [],
    canUndo: false, undo: vi.fn(), click: vi.fn(), stroke: vi.fn(), unoutlined: 0, outlineAll: vi.fn(),
    ...overrides,
  };
}

describe('MaskEditBar (doc 106)', () => {
  it('offers brush and eraser only on an outline, and clicks on any selection', () => {
    render(<MaskEditBar editing={editing()} selection="box" disabled={false} />);
    expect(screen.getByRole('radio', { name: '⊕ Add' })).toBeEnabled();
    expect(screen.getByRole('radio', { name: 'Brush' })).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('⊕ Add makes one');
  });

  it('counts the boxes it can outline, and runs them', async () => {
    const user = userEvent.setup();
    const state = editing({ unoutlined: 3 });
    render(<MaskEditBar editing={state} selection="none" disabled={false} />);
    await user.click(screen.getByRole('button', { name: 'Outlines from my boxes (3)' }));
    expect(state.outlineAll).toHaveBeenCalled();
  });

  it('shows the size while painting, and the error', () => {
    render(<MaskEditBar editing={editing({ tool: 'erase', radius: 12, error: 'Nothing would be left' })} selection="outline" disabled={false} />);
    expect(screen.getByText('12 px')).toBeInTheDocument();
    expect(screen.getByRole('alert')).toHaveTextContent('Nothing would be left');
  });
});

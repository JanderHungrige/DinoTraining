import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { GeneratorActionBar, type GeneratorActionBarProps } from './GeneratorActionBar';

function props(overrides: Partial<GeneratorActionBarProps> = {}): GeneratorActionBarProps {
  return {
    proposeLabel: 'Propose boxes',
    proposing: false,
    saving: false,
    dirty: true,
    canGoPrevious: true,
    canGoNext: true,
    autoPropose: true,
    autoSave: true,
    onAutoProposeChange: vi.fn(),
    onAutoSaveChange: vi.fn(),
    onPropose: vi.fn(),
    onSave: vi.fn(),
    onPrevious: vi.fn(),
    onNext: vi.fn(),
    ...overrides,
  };
}

describe('GeneratorActionBar (doc 70)', () => {
  it('keeps Propose, Save, Previous and Next together, in that order', () => {
    render(<GeneratorActionBar {...props()} />);
    const bar = screen.getByRole('toolbar', { name: /review this image/i });
    const names = within(bar)
      .getAllByRole('button')
      .map((button) => button.textContent);
    expect(names).toEqual(['Propose boxes', 'Save to dataset', '← Previous', 'Next →']);
    // The spacer that pushed Previous/Next to the far edge is gone.
    expect(bar.querySelector('.studio__spacer')).toBeNull();
  });

  it('gives each auto box a name that says what it automates', () => {
    render(<GeneratorActionBar {...props()} />);
    // Visible, not only for screen readers: a bare "auto" left people guessing.
    expect(screen.getByText('Auto-propose')).toBeInTheDocument();
    expect(screen.getByText('Auto-save')).toBeInTheDocument();
    expect(
      screen.getByRole('checkbox', { name: /propose automatically/i }),
    ).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /save automatically/i })).toBeChecked();
  });

  it('puts the automation boxes in their own row below the buttons', () => {
    render(<GeneratorActionBar {...props()} options={<input type="checkbox" aria-label="extra" />} />);
    const bar = screen.getByRole('toolbar', { name: /review this image/i });
    const row = screen.getByRole('group', { name: /automation/i });
    expect(within(bar).queryAllByRole('checkbox')).toHaveLength(0);
    expect(within(row).getAllByRole('checkbox')).toHaveLength(3);
    // Below, in document order.
    expect(bar.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it('reports toggling each box separately', async () => {
    const user = userEvent.setup();
    const onAutoProposeChange = vi.fn();
    const onAutoSaveChange = vi.fn();
    render(<GeneratorActionBar {...props({ onAutoProposeChange, onAutoSaveChange })} />);

    await user.click(screen.getByRole('checkbox', { name: /save automatically/i }));
    expect(onAutoSaveChange).toHaveBeenCalledWith(false);
    expect(onAutoProposeChange).not.toHaveBeenCalled();
  });

  it('disables Save until there is something to save', () => {
    render(<GeneratorActionBar {...props({ dirty: false })} />);
    expect(screen.getByRole('button', { name: /save to dataset/i })).toBeDisabled();
  });

  it('holds navigation while a save is in flight — leaving mid-save would drop it', () => {
    render(<GeneratorActionBar {...props({ saving: true })} />);
    expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
  });

  it('locks every control while autoplay drives the session', () => {
    render(<GeneratorActionBar {...props({ locked: true })} />);
    for (const button of screen.getAllByRole('button')) expect(button).toBeDisabled();
    for (const box of screen.getAllByRole('checkbox')) expect(box).toBeDisabled();
  });
});

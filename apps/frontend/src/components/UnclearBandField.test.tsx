import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { UnclearBandField } from './UnclearBandField';
import { UnclearQuestion } from './UnclearQuestion';

const BAND = { low: 0.3, high: 0.5 };

describe('UnclearBandField (doc 72)', () => {
  it('keeps the bounds inert until asking is switched on', () => {
    render(
      <UnclearBandField
        enabled={false}
        band={BAND}
        disabled={false}
        onEnabledChange={vi.fn()}
        onBandChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('spinbutton', { name: /lowest score/i })).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: /ask me when a score is between/i })).not.toBeChecked();
  });

  it('reports each bound as a number', () => {
    const onBandChange = vi.fn();
    render(
      <UnclearBandField
        enabled
        band={BAND}
        disabled={false}
        onEnabledChange={vi.fn()}
        onBandChange={onBandChange}
      />,
    );
    fireEvent.change(screen.getByRole('spinbutton', { name: /highest score/i }), {
      target: { value: '0.65' },
    });
    expect(onBandChange).toHaveBeenCalledWith({ low: 0.3, high: 0.65 });
  });

  it('cannot be changed mid-run', () => {
    render(
      <UnclearBandField
        enabled
        band={BAND}
        disabled
        onEnabledChange={vi.fn()}
        onBandChange={vi.fn()}
      />,
    );
    expect(screen.getByRole('checkbox')).toBeDisabled();
  });
});

describe('UnclearQuestion (doc 72)', () => {
  it('says where it stopped and why, and takes focus', () => {
    render(
      <UnclearQuestion
        imageNumber={12}
        imageTotal={289}
        count={2}
        band={BAND}
        onContinue={vi.fn()}
        onStop={vi.fn()}
      />,
    );
    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('Paused on image 12 of 289');
    expect(alert).toHaveTextContent('2 proposals scored between 0.30 and 0.50');
    expect(screen.getByRole('button', { name: 'Continue' })).toHaveFocus();
  });

  it('continues or stops on request', async () => {
    const user = userEvent.setup();
    const onContinue = vi.fn();
    const onStop = vi.fn();
    render(
      <UnclearQuestion
        imageNumber={1}
        imageTotal={3}
        count={1}
        band={BAND}
        onContinue={onContinue}
        onStop={onStop}
      />,
    );
    await user.click(screen.getByRole('button', { name: 'Continue' }));
    await user.click(screen.getByRole('button', { name: /stop here/i }));
    expect(onContinue).toHaveBeenCalledTimes(1);
    expect(onStop).toHaveBeenCalledTimes(1);
  });
});

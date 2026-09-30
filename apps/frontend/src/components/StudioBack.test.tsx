import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { StudioBack } from './StudioBack';

function setup(dirty: boolean, saved = true) {
  const onSave = vi.fn(async () => saved);
  const onBack = vi.fn();
  render(<StudioBack dirty={dirty} busy={false} onSave={onSave} onBack={onBack} />);
  return { onSave, onBack, user: userEvent.setup() };
}

describe('StudioBack', () => {
  it('goes straight back when nothing is unsaved', async () => {
    const { onBack, user } = setup(false);
    await user.click(screen.getByRole('button', { name: '← Back to overview' }));
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('asks first when the picture has unsaved changes, and Stay keeps the session', async () => {
    const { onBack, user } = setup(true);
    await user.click(screen.getByRole('button', { name: '← Back to overview' }));
    expect(onBack).not.toHaveBeenCalled();
    expect(screen.getByText(/They are lost if you go back without saving/)).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Stay' }));
    expect(screen.queryByText(/They are lost/)).not.toBeInTheDocument();
    expect(onBack).not.toHaveBeenCalled();
  });

  it('saves and then goes back', async () => {
    const { onSave, onBack, user } = setup(true);
    await user.click(screen.getByRole('button', { name: '← Back to overview' }));
    await user.click(screen.getByRole('button', { name: 'Save and go back' }));
    expect(onSave).toHaveBeenCalledOnce();
    expect(onBack).toHaveBeenCalledOnce();
  });

  it('stays when the save fails, so nothing is lost', async () => {
    const { onBack, user } = setup(true, false);
    await user.click(screen.getByRole('button', { name: '← Back to overview' }));
    await user.click(screen.getByRole('button', { name: 'Save and go back' }));
    expect(onBack).not.toHaveBeenCalled();
  });

  it('discards on request', async () => {
    const { onSave, onBack, user } = setup(true);
    await user.click(screen.getByRole('button', { name: '← Back to overview' }));
    await user.click(screen.getByRole('button', { name: 'Go back without saving' }));
    expect(onSave).not.toHaveBeenCalled();
    expect(onBack).toHaveBeenCalledOnce();
  });
});

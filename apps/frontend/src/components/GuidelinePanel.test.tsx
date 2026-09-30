import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { GuidelinePanel } from './GuidelinePanel';

vi.mock('../api/quality', () => ({ getGuideline: vi.fn(), saveGuideline: vi.fn() }));
const api = await import('../api/quality');

beforeEach(() => vi.clearAllMocks());

describe('GuidelinePanel (doc 109)', () => {
  it('opens by itself when there is a guideline, so the next annotator reads it first', async () => {
    vi.mocked(api.getGuideline).mockResolvedValue('Rings: hole filled.');
    render(<GuidelinePanel datasetId="d1" />);
    const box = await screen.findByRole('textbox', { name: 'Annotation guideline' });
    expect(box).toHaveValue('Rings: hole filled.');
    expect(box.closest('details')).toHaveAttribute('open');
  });

  it('stays folded when empty, and saves what is written', async () => {
    const user = userEvent.setup();
    vi.mocked(api.getGuideline).mockResolvedValue('');
    vi.mocked(api.saveGuideline).mockImplementation(async (_id: string, text: string) => text);
    render(<GuidelinePanel datasetId="d1" />);
    expect(await screen.findByText('Annotation guideline (none yet)')).toBeInTheDocument();
    const save = screen.getByRole('button', { name: 'Save guideline' });
    expect(save).toBeDisabled();
    await user.type(screen.getByRole('textbox', { name: 'Annotation guideline' }), 'Poles count.');
    await user.click(save);
    expect(api.saveGuideline).toHaveBeenCalledWith('d1', 'Poles count.');
    expect(await screen.findByRole('status')).toHaveTextContent('Saved.');
  });
});

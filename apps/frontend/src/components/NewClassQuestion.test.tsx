import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { NewClassQuestion } from './NewClassQuestion';

vi.mock('../api/phrases', async () => {
  const actual = await vi.importActual<typeof import('../api/phrases')>('../api/phrases');
  return { ...actual, getCompleteness: vi.fn(), markAbsentInOlder: vi.fn() };
});
const api = await import('../api/phrases');

const M10 = { m8: { since: 'a', unknown: 0 }, m10: { since: 'b', unknown: 20 } };

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});

describe('NewClassQuestion (doc 118)', () => {
  it('asks about a class with pictures saved before it, and says nothing otherwise', async () => {
    vi.mocked(api.getCompleteness).mockResolvedValue(M10);
    render(<NewClassQuestion datasetId="d1" watch="" />);
    expect(await screen.findByText('m10 is new. 20 pictures were saved before it.')).toBeInTheDocument();
    expect(screen.queryByText(/m8 is new/)).not.toBeInTheDocument();
  });

  it('"It does not occur there" marks them absent and looks again', async () => {
    const user = userEvent.setup();
    vi.mocked(api.getCompleteness).mockResolvedValueOnce(M10).mockResolvedValue({ ...M10, m10: { since: 'b', unknown: 0 } });
    vi.mocked(api.markAbsentInOlder).mockResolvedValue({ marked: 20 });
    render(<NewClassQuestion datasetId="d1" watch="" />);
    await user.click(await screen.findByRole('button', { name: 'It does not occur there' }));
    expect(api.markAbsentInOlder).toHaveBeenCalledWith('d1', 'm10');
    expect(await screen.findByText('20 pictures marked: no m10.')).toBeInTheDocument();
    expect(screen.queryByText(/m10 is new/)).not.toBeInTheDocument();
  });

  it('"Review them later" keeps a one-line reminder with Review for, remembered', async () => {
    const user = userEvent.setup();
    const onReview = vi.fn();
    vi.mocked(api.getCompleteness).mockResolvedValue(M10);
    const { unmount } = render(<NewClassQuestion datasetId="d1" watch="" onReview={onReview} />);
    await user.click(await screen.findByRole('button', { name: 'Review them later' }));
    expect(api.markAbsentInOlder).not.toHaveBeenCalled();
    expect(screen.getByText('m10: 20 pictures not reviewed yet.')).toBeInTheDocument();
    unmount();
    render(<NewClassQuestion datasetId="d1" watch="" onReview={onReview} />);
    await user.click(await screen.findByRole('button', { name: 'Review for m10' }));
    expect(onReview).toHaveBeenCalledWith('m10');
  });
});

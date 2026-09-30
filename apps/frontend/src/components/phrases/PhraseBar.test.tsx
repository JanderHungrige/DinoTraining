import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PhraseInfo } from '../../api/phrases';
import type { PicturePhrases } from '../../hooks/usePicturePhrases';
import type { CanvasBox } from '../../types/annotation';
import { PhraseBar } from './PhraseBar';

vi.mock('../../api/phrases', async () => {
  const actual = await vi.importActual<typeof import('../../api/phrases')>('../../api/phrases');
  return { ...actual, addPhrase: vi.fn(), changePhrase: vi.fn(), markTheRest: vi.fn() };
});
const api = await import('../../api/phrases');

const P = (text: string, className = text, variants: string[] = []): PhraseInfo => ({
  id: 1, text, class_name: className, variants, confusable: [], instances: 3, complete: 0, absent: 0,
});
const MASK = { rle: { size: [1, 1] as [number, number], counts: [0, 1] }, png: '' };
const OUTLINE: CanvasBox = { id: 'm1', label: 'positive', provenance: 'sam3', x: 0, y: 0, w: 1, h: 1, text: 'car', mask: MASK };

function pictures(phrases: PhraseInfo[]): PicturePhrases {
  return { phrases, statuses: [], error: '', reload: vi.fn(), mark: vi.fn(async () => undefined) };
}

function renderBar(phrases: PhraseInfo[], selectedId: string | null = 'm1') {
  const state = pictures(phrases);
  const onBoxesChange = vi.fn();
  render(
    <PhraseBar datasetId="d1" items={[{ box: OUTLINE, number: 1 }]} selectedId={selectedId} pictures={state} onBoxesChange={onBoxesChange} open disabled={false} />,
  );
  return { state, onBoxesChange };
}

beforeEach(() => vi.mocked(api.addPhrase).mockReset());

describe('PhraseBar (doc 105)', () => {
  it('shows every phrase as a chip with its count and variations, keys 1–9 pick one', async () => {
    const user = userEvent.setup();
    renderBar([P('car', 'car', ['automobile']), P('red car', 'car')]);
    const car = screen.getByRole('button', { name: /car 3/ , pressed: true });
    expect(car).toHaveAttribute('title', 'Also: automobile');
    await user.keyboard('2');
    expect(screen.getByRole('button', { name: /red car 3/, pressed: true })).toBeInTheDocument();
  });

  it('A and N mark the active phrase for this picture; never while typing', async () => {
    const user = userEvent.setup();
    const { state } = renderBar([P('car')]);
    await user.keyboard('a');
    expect(state.mark).toHaveBeenCalledWith('car', 'complete');
    await user.type(screen.getByLabelText('+ phrase'), 'an');
    expect(state.mark).toHaveBeenCalledTimes(1);
  });

  it('adds a phrase with comma variations under the selected outline\'s class', async () => {
    const user = userEvent.setup();
    vi.mocked(api.addPhrase).mockResolvedValue(P('red car', 'car', ['crimson car']));
    const { state } = renderBar([P('car')]);
    await user.type(screen.getByLabelText('+ phrase'), 'red car, crimson car{Enter}');
    expect(api.addPhrase).toHaveBeenCalledWith('d1', 'red car, crimson car', 'car');
    expect(state.reload).toHaveBeenCalled();
  });

  it('puts the active phrase on the selected outline', async () => {
    const user = userEvent.setup();
    const { onBoxesChange } = renderBar([P('car'), P('red car', 'car')]);
    await user.keyboard('2');
    await user.click(screen.getByRole('button', { name: 'Add “red car”' }));
    expect(onBoxesChange).toHaveBeenCalledWith([expect.objectContaining({ id: 'm1', phrases: ['car', 'red car'] })]);
  });

  it('does not offer another class\'s phrase, and says why', async () => {
    const user = userEvent.setup();
    renderBar([P('car'), P('red light', 'signal')]);
    await user.keyboard('2');
    expect(screen.getByRole('button', { name: 'Add “red light”' })).toBeDisabled();
    expect(screen.getByText(/phrase of class signal/)).toBeInTheDocument();
  });

  it('explains variations and hard negatives where they are used', () => {
    renderBar([P('car')]);
    expect(screen.getByText('How phrases work')).toBeInTheDocument();
    expect(screen.getByText(/You do not need every synonym/)).toBeInTheDocument();
    expect(screen.getByText(/num_cross_negatives/)).toBeInTheDocument();
  });
});

describe('Mark the rest (doc 108, amended)', () => {
  it('checks every remaining picture of a fully annotated phrase, and says how many', async () => {
    const user = userEvent.setup();
    vi.mocked(api.markTheRest).mockResolvedValue({ complete: 40, absent: 30 });
    const { state } = renderBar([P('car')]);
    await user.click(screen.getByText('Manage phrases'));
    await user.click(screen.getByRole('button', { name: 'Mark the rest' }));
    expect(api.markTheRest).toHaveBeenCalledWith('d1', 'car');
    expect(await screen.findByText('Marked 40 all marked, 30 not in this picture.')).toBeInTheDocument();
    expect(state.reload).toHaveBeenCalled();
  });
});

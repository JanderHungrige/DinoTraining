import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { PhraseInfo } from '../../api/phrases';
import type { PicturePhrases } from '../../hooks/usePicturePhrases';
import { PhraseBar } from './PhraseBar';

vi.mock('../../api/phrases', async () => {
  const actual = await vi.importActual<typeof import('../../api/phrases')>('../../api/phrases');
  return { ...actual, addPhrase: vi.fn(), addUmbrella: vi.fn(), changePhrase: vi.fn(), markTheRest: vi.fn(), deletePhrase: vi.fn() };
});
const api = await import('../../api/phrases');

const P = (text: string, className = text, extra: Partial<PhraseInfo> = {}): PhraseInfo => ({
  id: 1, text, class_name: className, variants: [], confusable: [], instances: 3, complete: 0, absent: 0,
  classes: [className], umbrella: false, ...extra,
});
const SCREW = P('screw', '', { id: 9, umbrella: true, classes: ['m8', 'm9'], instances: 6 });

function pictures(phrases: PhraseInfo[]): PicturePhrases {
  return { phrases, statuses: [], error: '', reload: vi.fn(), mark: vi.fn(async () => undefined) };
}

function renderBar(phrases: PhraseInfo[]) {
  const state = pictures(phrases);
  render(<PhraseBar datasetId="d1" pictures={state} open disabled={false} />);
  return state;
}

beforeEach(() => vi.clearAllMocks());

describe('PhraseBar (doc 116)', () => {
  it('shows classes and umbrella terms with their counts, and creates no class', () => {
    renderBar([P('m8'), P('m9'), SCREW]);
    expect(screen.getByRole('button', { name: /screw 6/ })).toHaveAttribute('title', expect.stringContaining('Umbrella over m8, m9'));
    expect(screen.queryByLabelText('belongs to')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('+ phrase')).not.toBeInTheDocument();
  });

  it('adds an umbrella term over the ticked classes', async () => {
    const user = userEvent.setup();
    vi.mocked(api.addUmbrella).mockResolvedValue(SCREW);
    const state = renderBar([P('m8'), P('m9'), P('nut')]);
    await user.type(screen.getByLabelText('+ Umbrella term'), 'screw');
    await user.click(screen.getByRole('checkbox', { name: 'm8' }));
    await user.click(screen.getByRole('checkbox', { name: 'm9' }));
    await user.click(screen.getByRole('button', { name: 'Add' }));
    expect(api.addUmbrella).toHaveBeenCalledWith('d1', 'screw', ['m8', 'm9']);
    expect(state.reload).toHaveBeenCalled();
    expect(api.addPhrase).not.toHaveBeenCalled();
  });

  it('asks for two classes before sending, and says why with fewer than two in the dataset', async () => {
    const user = userEvent.setup();
    renderBar([P('m8'), P('m9')]);
    await user.type(screen.getByLabelText('+ Umbrella term'), 'screw');
    await user.click(screen.getByRole('checkbox', { name: 'm8' }));
    await user.click(screen.getByRole('button', { name: 'Add' }));
    expect(screen.getByRole('alert')).toHaveTextContent('Tick at least two classes.');
    expect(api.addUmbrella).not.toHaveBeenCalled();
  });

  it('offers no umbrella with a single class', () => {
    renderBar([P('m8')]);
    expect(screen.getByText(/needs two classes/)).toBeInTheDocument();
  });

  it('keys do nothing while the checks are folded, and mark once they are open', async () => {
    const user = userEvent.setup();
    const state = renderBar([P('m8')]);
    await user.keyboard('a');
    expect(state.mark).not.toHaveBeenCalled();
    await user.click(screen.getByText('Only for imported or partly annotated datasets'));
    await user.keyboard('a');
    expect(state.mark).toHaveBeenCalledWith('m8', 'complete');
    expect(screen.getByRole('button', { name: 'Not in this picture' })).toBeInTheDocument();
  });

  it('Mark the rest lives with the checks', async () => {
    const user = userEvent.setup();
    vi.mocked(api.markTheRest).mockResolvedValue({ complete: 40, absent: 30 });
    const state = renderBar([P('m8'), P('m9')]);
    await user.click(screen.getByText('Only for imported or partly annotated datasets'));
    await user.selectOptions(screen.getByLabelText('Mark the rest for'), 'm9');
    await user.click(screen.getByRole('button', { name: 'Mark the rest' }));
    expect(api.markTheRest).toHaveBeenCalledWith('d1', 'm9');
    expect(await screen.findByText('Marked 40 all marked, 30 not in this picture.')).toBeInTheDocument();
    expect(state.reload).toHaveBeenCalled();
  });

  it('explains classes, umbrella terms and look-alikes', () => {
    renderBar([P('m8')]);
    expect(screen.getByText('Umbrella terms')).toBeInTheDocument();
    expect(screen.getByText(/finds every m8 and m9/)).toBeInTheDocument();
    expect(screen.getByText(/rarely share a picture with the class/)).toBeInTheDocument();
  });
});

describe('Manage phrases (doc 116)', () => {
  it('shows an umbrella with its classes, and an older sub-phrase as such, both deletable', async () => {
    const user = userEvent.setup();
    vi.mocked(api.deletePhrase).mockResolvedValue({ removed: true });
    const state = renderBar([P('m8', 'm8', { id: null }), SCREW, P('red m8', 'm8', { id: 4 })]);
    await user.click(screen.getByText('Manage phrases'));
    const items = screen.getAllByRole('listitem');
    expect(items[1]).toHaveTextContent('umbrella over m8, m9');
    expect(items[2]).toHaveTextContent('Older sub-phrase of class m8');
    expect(within(items[2]!).queryByLabelText('Variations')).not.toBeInTheDocument();
    expect(within(items[0]!).queryByRole('button', { name: 'Delete' })).not.toBeInTheDocument();
    await user.click(within(items[2]!).getByRole('button', { name: 'Delete' }));
    await user.click(within(items[2]!).getByRole('button', { name: 'Delete' }));
    expect(api.deletePhrase).toHaveBeenCalledWith('d1', 4);
    expect(state.reload).toHaveBeenCalled();
  });

  it('saves a class’s variations and look-alikes', async () => {
    const user = userEvent.setup();
    vi.mocked(api.changePhrase).mockResolvedValue(P('m8'));
    renderBar([P('m8')]);
    await user.click(screen.getByText('Manage phrases'));
    await user.type(screen.getByLabelText('Not to be confused with'), 'nail');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(api.changePhrase).toHaveBeenCalledWith('d1', 1, { confusable: ['nail'] });
  });
});

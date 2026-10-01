import type { JSX } from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ParameterInfo, ParameterSetInfo } from '../../api/parameters';
import { useParameters } from '../../hooks/useParameters';
import { blockingParameter, ParameterForm } from './ParameterForm';

vi.mock('../../api/parameters', async () => {
  const actual = await vi.importActual<typeof import('../../api/parameters')>('../../api/parameters');
  return { ...actual, getParameters: vi.fn() };
});
const api = await import('../../api/parameters');

function parameter(overrides: Partial<ParameterInfo>): ParameterInfo {
  return {
    key: 'epochs', label: 'Rounds', term: 'epochs', help: 'How many times training goes through all pictures.',
    default: 20, why: 'Enough for a few hundred pictures.', kind: 'int', level: 'basic',
    minimum: 1, maximum: 1000, choices: [], recipe_overrides: false, ...overrides,
  };
}

const SET: ParameterSetInfo = {
  family: 'head', title: 'DINO head', covers: '',
  parameters: [
    parameter({}),
    parameter({ key: 'learning_rate', label: 'Learning speed', term: 'learning rate', default: 0.001, kind: 'float', minimum: 1e-6, maximum: 1 }),
    parameter({ key: 'weight_decay', label: 'Weight shrinkage', term: 'weight decay', default: 0.01, kind: 'float', level: 'advanced', minimum: 0, maximum: 1 }),
    parameter({
      key: 'lr_schedule', label: 'Speed schedule', term: 'learning-rate schedule', default: 'constant', kind: 'choice', level: 'advanced',
      minimum: null, maximum: null, choices: [{ value: 'constant', label: 'Constant' }, { value: 'cosine', label: 'Slow down (cosine)' }],
    }),
    parameter({ key: 'val_fraction', label: 'Validation share', term: 'validation fraction', default: 0.2, kind: 'float', level: 'advanced', minimum: 0, maximum: 0.5, recipe_overrides: true }),
  ],
};

function Harness({ recipe = false }: { readonly recipe?: boolean }): JSX.Element {
  const params = useParameters('head');
  return (
    <>
      <ParameterForm params={params} recipeChosen={recipe} />
      <output data-testid="values">{JSON.stringify(params.values)}</output>
      <output data-testid="blocked">{blockingParameter(params)}</output>
    </>
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(api.getParameters).mockResolvedValue(SET);
});

describe('ParameterForm (doc 100)', () => {
  it('labels each field "Plain name (technical term)"', async () => {
    render(<Harness />);
    expect(await screen.findByLabelText('Rounds (epochs)')).toHaveValue('20');
    expect(screen.getByLabelText('Learning speed (learning rate)')).toHaveValue('0.001');
  });

  it('does not repeat the term when the label already is it (German, Jan 2026-09-30)', async () => {
    vi.mocked(api.getParameters).mockResolvedValue({ ...SET, parameters: [parameter({ label: 'Epochs' })] });
    render(<Harness />);
    expect(await screen.findByLabelText('Epochs')).toHaveValue('20');
    expect(screen.queryByText('(epochs)')).not.toBeInTheDocument();
  });

  it('opens the ? with the explanation, the default and why; Esc closes it and returns focus', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const help = await screen.findByRole('button', { name: 'About Rounds' });
    expect(help).toHaveAttribute('aria-expanded', 'false');
    await user.click(help);
    const note = screen.getByRole('note');
    expect(note).toHaveTextContent('How many times training goes through all pictures.');
    expect(note).toHaveTextContent('Default: 20 — Enough for a few hundred pictures.');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('note')).toBeNull();
    expect(help).toHaveFocus();
  });

  it('tells a screen reader the explanation without opening anything', async () => {
    render(<Harness />);
    const field = await screen.findByLabelText('Rounds (epochs)');
    expect(field).toHaveAccessibleDescription(/How many times training .* Default: 20\./);
  });

  it('keeps advanced settings folded and counts the changed ones', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const summary = await screen.findByText('Advanced settings');
    expect(summary.closest('details')).not.toHaveAttribute('open');
    await user.click(summary);
    await user.selectOptions(screen.getByLabelText('Speed schedule (learning-rate schedule)'), 'cosine');
    expect(screen.getByText('Advanced settings (1 changed)')).toBeInTheDocument();
    expect(JSON.parse(screen.getByTestId('values').textContent!)).toMatchObject({ lr_schedule: 'cosine', epochs: 20 });
  });

  it('marks a changed field, resets it, and resets all', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const rounds = await screen.findByLabelText('Rounds (epochs)');
    await user.clear(rounds);
    await user.type(rounds, '35');
    const reset = screen.getByRole('button', { name: 'Reset Rounds to 20' });
    await user.click(reset);
    expect(rounds).toHaveValue('20');
    await user.clear(rounds);
    await user.type(rounds, '3');
    await user.click(screen.getByRole('button', { name: 'Reset all to defaults' }));
    expect(rounds).toHaveValue('20');
    expect(screen.queryByRole('button', { name: 'Reset all to defaults' })).toBeNull();
  });

  it('keeps a small learning rate exactly, and types through "1e-" without losing it', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const rate = await screen.findByLabelText('Learning speed (learning rate)');
    await user.clear(rate);
    await user.type(rate, '1e-5');
    expect(rate).toHaveValue('1e-5');
    expect(JSON.parse(screen.getByTestId('values').textContent!).learning_rate).toBe(0.00001);
  });

  it('says what is out of range at the field and names it for the Start button', async () => {
    const user = userEvent.setup();
    render(<Harness />);
    const rounds = await screen.findByLabelText('Rounds (epochs)');
    await user.clear(rounds);
    await user.type(rounds, '0');
    expect(screen.getByRole('alert')).toHaveTextContent('Between 1 and 1000.');
    expect(screen.getByTestId('blocked')).toHaveTextContent('Rounds: Between 1 and 1000.');
  });

  it('shows what a recipe sets, but does not let it be edited', async () => {
    const user = userEvent.setup();
    render(<Harness recipe />);
    await user.click(await screen.findByText('Advanced settings'));
    const share = screen.getByLabelText('Validation share (validation fraction)');
    expect(share).toBeDisabled();
    expect(within(share.closest('.param-field') as HTMLElement).getByText('Set by the recipe')).toBeInTheDocument();
  });

  it('remembers a change per model family', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<Harness />);
    const rounds = await screen.findByLabelText('Rounds (epochs)');
    await user.clear(rounds);
    await user.type(rounds, '12');
    unmount();
    render(<Harness />);
    expect(await screen.findByLabelText('Rounds (epochs)')).toHaveValue('12');
  });
});

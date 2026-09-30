import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { readPersisted, isString } from '../lib/persisted';
import { RecipeExplainer } from './RecipeExplainer';

vi.mock('../api/defaultRecipe', () => ({
  startDefaultRecipe: vi.fn(),
  getDefaultRecipeJob: vi.fn(),
  resolveTarget: vi.fn(),
}));
const api = await import('../api/defaultRecipe');

const RECIPE = { id: 'r9', name: 'Default for SAM 3', version: 1 } as never;

beforeEach(() => {
  localStorage.clear();
  vi.mocked(api.startDefaultRecipe).mockResolvedValue({ job_id: 'j', state: 'running', message: 'Starting…', recipe: null });
  vi.mocked(api.getDefaultRecipeJob)
    .mockResolvedValueOnce({ job_id: 'j', state: 'running', message: 'Splitting without leaks…', recipe: null })
    .mockResolvedValue({ job_id: 'j', state: 'complete', message: 'Saved.', recipe: RECIPE });
  vi.mocked(api.resolveTarget).mockResolvedValue({ target: 'sam3', label: 'Fine-tune SAM 3' });
});

describe('RecipeExplainer (doc 101)', () => {
  it('explains what a recipe is, what skipping one costs, and where they are made', () => {
    render(<RecipeExplainer datasetId="d1" model={{ model_id: 'sam3' }} onSaved={vi.fn()} />);
    expect(screen.getByRole('heading', { name: 'What is a recipe?' })).toBeInTheDocument();
    expect(screen.getByText(/one dataset for one model/)).toBeInTheDocument();
    expect(screen.getByText(/score looks better than the model is/)).toBeInTheDocument();
    expect(screen.getByText(/Prepare data/, { selector: 'strong' })).toBeInTheDocument();
  });

  it('says so when the model cannot start without one', () => {
    render(<RecipeExplainer datasetId="d1" model={{ model_id: 'sam3' }} required onSaved={vi.fn()} />);
    expect(screen.getByRole('heading', { name: 'What is a recipe? This model needs one.' })).toBeInTheDocument();
  });

  it('makes the default recipe, shows the step it is on, and hands the recipe over', async () => {
    const user = userEvent.setup();
    const onSaved = vi.fn();
    render(<RecipeExplainer datasetId="d1" model={{ model_id: 'sam3' }} onSaved={onSaved} />);
    await user.click(screen.getByRole('button', { name: 'Create the default recipe' }));
    expect(api.startDefaultRecipe).toHaveBeenCalledWith('d1', { model_id: 'sam3' });
    expect(await screen.findByText('Splitting without leaks…')).toBeInTheDocument();
    await waitFor(() => expect(onSaved).toHaveBeenCalledWith(RECIPE), { timeout: 3000 });
  });

  it('waits for a model before it can make one, and says why', () => {
    render(<RecipeExplainer datasetId="d1" model={null} modelMissing="Choose a head type first." onSaved={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Create the default recipe' })).toBeDisabled();
    expect(screen.getByText('Choose a head type first.')).toBeInTheDocument();
  });

  it('opens Prepare data at this dataset and model', async () => {
    const user = userEvent.setup();
    const onOpenPrepare = vi.fn();
    render(<RecipeExplainer datasetId="d1" model={{ model_id: 'sam3' }} onSaved={vi.fn()} onOpenPrepare={onOpenPrepare} />);
    await user.click(screen.getByRole('button', { name: 'Open Prepare data' }));
    await waitFor(() => expect(onOpenPrepare).toHaveBeenCalled());
    expect(readPersisted('prepare.dataset', '', isString)).toBe('d1');
    expect(readPersisted('prepare.target', '', isString)).toBe('sam3');
  });

  it('shows a failed job with its reason', async () => {
    const user = userEvent.setup();
    vi.mocked(api.getDefaultRecipeJob).mockReset().mockResolvedValue({ job_id: 'j', state: 'failed', message: 'There are no images to split.', recipe: null });
    render(<RecipeExplainer datasetId="d1" model={{ model_id: 'sam3' }} onSaved={vi.fn()} />);
    await user.click(screen.getByRole('button', { name: 'Create the default recipe' }));
    expect(await screen.findByRole('alert', {}, { timeout: 3000 })).toHaveTextContent('There are no images to split.');
  });
});

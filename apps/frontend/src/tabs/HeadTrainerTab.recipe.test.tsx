/**
 * Training from a preparation recipe (doc 90): the jump from Prepare data chooses the
 * dataset and the recipe, and the run is started with it.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as foundation from '../api/foundation';
import * as heads from '../api/headInstances';
import * as prepPlan from '../api/prepPlan';
import * as training from '../api/training';
import * as trainerOptions from '../hooks/useTrainerOptions';
import { effectiveRecipe, NO_RECIPE } from '../hooks/useRecipeChoice';
import { HeadTrainerTab } from './HeadTrainerTab';

vi.mock('../api/foundation');
vi.mock('../api/headInstances');
vi.mock('../api/prepPlan', async () => {
  const actual = await vi.importActual<typeof import('../api/prepPlan')>('../api/prepPlan');
  return { ...actual, listRecipes: vi.fn() };
});
vi.mock('../api/training', async () => {
  const actual = await vi.importActual<typeof import('../api/training')>('../api/training');
  return { ...actual, startTraining: vi.fn(), streamTrainingJob: vi.fn(() => () => undefined) };
});

function recipe(id: string, version: number, outOfDate: string[] = []): prepPlan.RecipeInfo {
  return {
    recipe: { id, name: 'cells', version, target: 'head-detection-dinov2', imbalance: 'weighted-loss', augmentation: 'microscopy' } as never,
    out_of_date: outOfDate,
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(heads.listHeadInstances).mockResolvedValue([]);
  vi.mocked(foundation.listFoundations).mockResolvedValue([]);
  vi.mocked(prepPlan.listRecipes).mockResolvedValue([recipe('r1', 1), recipe('r2', 2), recipe('r3', 3, ['The split changed.'])]);
  vi.mocked(training.startTraining).mockResolvedValue({
    job_id: 'j', state: 'pending', epoch: 0, total_epochs: 1, history: [], class_names: [],
    skipped_mixed_class_images: 0, best_metric: null, best_epoch: null, primary_metric: 'map',
    message: '', head_instance_id: null, head_type_id: 'dense-detector', backbone_id: 'dinov2-small',
    dataset_ids: ['d1'],
  } as never);
  vi.spyOn(trainerOptions, 'useTrainerOptions').mockReturnValue({
    datasets: [{ id: 'd1', name: 'Cells', counts: { images: 3 } }],
    backbones: [{ id: 'dinov2-small', installed: true, family: 'dinov2' }],
    headTypes: [{ id: 'dense-detector', task: 'detection', title: 'Detector', description: '', metrics: ['map'], trainable: true, compatible: true }],
    loading: false,
    error: null,
  } as unknown as ReturnType<typeof trainerOptions.useTrainerOptions>);
});

describe('which recipe a run follows', () => {
  it('defaults to the latest recipe that still describes the data, and "none" means none', () => {
    const list = [recipe('r1', 1), recipe('r2', 2), recipe('r3', 3, ['changed'])];
    expect(effectiveRecipe(list, '')?.recipe.id).toBe('r2');
    expect(effectiveRecipe(list, 'r1')?.recipe.id).toBe('r1');
    expect(effectiveRecipe(list, NO_RECIPE)).toBeNull();
  });

  it('starts the run with the recipe the Prepare tab sent', async () => {
    const user = userEvent.setup();
    render(<HeadTrainerTab request={{ datasetId: 'd1', recipeId: 'r1', nonce: 1 }} />);
    const picker = await screen.findByRole('combobox', { name: 'Preparation recipe' });
    await waitFor(() => expect(picker).toHaveValue('r1'));
    expect(screen.getByRole('option', { name: /cells · v3 \(out of date\)/ })).toBeDisabled();

    await user.click(screen.getByRole('radio', { name: /Detector/ }));
    const start = screen.getByRole('button', { name: 'Start training' });
    await waitFor(() => expect(start).toBeEnabled());
    await user.click(start);
    await waitFor(() =>
      expect(training.startTraining).toHaveBeenCalledWith(expect.objectContaining({ dataset_ids: ['d1'], recipe_id: 'r1' })),
    );
  });
});

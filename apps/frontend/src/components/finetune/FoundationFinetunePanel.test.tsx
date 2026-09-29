import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { FinetuneRequirements, Readiness } from '../../api/finetune';
import { FoundationFinetunePanel } from './FoundationFinetunePanel';

vi.mock('../../api/finetune', async () => {
  const actual = await vi.importActual<typeof import('../../api/finetune')>('../../api/finetune');
  return { ...actual, listRequirements: vi.fn(), checkReadiness: vi.fn(), startFinetune: vi.fn() };
});
vi.mock('../../api/prepPlan', async () => {
  const actual = await vi.importActual<typeof import('../../api/prepPlan')>('../../api/prepPlan');
  return { ...actual, listRecipes: vi.fn(async () => [{ recipe: { id: 'r1', name: 'rings', version: 1, imbalance: 'none', augmentation: 'none' }, out_of_date: [] }]) };
});
const api = await import('../../api/finetune');

function spec(id: string, label: string, available = true): FinetuneRequirements {
  return {
    id, model_id: id, label, task: 'segmentation', annotation_kind: 'instance-masks', prompt_kind: 'box-from-mask',
    min_images: 20, min_instances_per_class: 50, minimums_why: 'Why.', image_sizes: 'Any.', recipe_required: true,
    gates: [], data_format: 'One mask per object.', what_trains: 'The mask decoder.', available,
    unavailable_reason: available ? '' : 'Built later.',
  };
}

function readiness(ready: boolean): Readiness {
  return {
    finetune_id: 'sam2.1-hiera-small', dataset_id: 'd1', recipe_id: 'r1', ready,
    checks: [{ id: 'per-class', title: 'At least 50 per class', passed: ready, detail: 'ring: 12', fix: ready ? '' : 'Annotate more of: ring' }],
  };
}

beforeEach(() => {
  localStorage.clear();
  vi.mocked(api.listRequirements).mockResolvedValue([spec('sam2.1-hiera-small', 'SAM 2.1 (small)'), spec('sam9', 'SAM 9', false), spec('dinov2-small-segmentation', 'DINOv2 ViT-S/14 — segmentation')]);
  vi.mocked(api.startFinetune).mockResolvedValue({ job_id: 'j', state: 'pending', epoch: 0, total_epochs: 6, history: [], notes: [] } as never);
});

const DATASETS = [{ id: 'd1', name: 'Rings', counts: { images: 70 } }] as never;

describe('FoundationFinetunePanel', () => {
  it('names the rule the data breaks and keeps Start off until it is met', async () => {
    vi.mocked(api.checkReadiness).mockResolvedValue(readiness(false));
    render(<FoundationFinetunePanel datasets={DATASETS} />);
    expect(await screen.findByText(/Annotate more of: ring/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Start fine-tuning' })).toBeDisabled();
    expect(screen.getByRole('option', { name: /SAM 9 \(not yet\)/ })).toBeDisabled();
    expect(screen.getByText('One mask per object.')).toBeInTheDocument(); // the data format, shown
  });

  it('starts with the recipe, and trains DINO backbone blocks when that is chosen', async () => {
    const user = userEvent.setup();
    vi.mocked(api.checkReadiness).mockResolvedValue(readiness(true));
    render(<FoundationFinetunePanel datasets={DATASETS} />);
    const model = await screen.findByRole('combobox', { name: 'Model' });
    await user.selectOptions(model, 'dinov2-small-segmentation');
    const start = screen.getByRole('button', { name: 'Start fine-tuning' });
    await waitFor(() => expect(start).toBeEnabled());
    await user.click(start);
    expect(api.startFinetune).toHaveBeenCalledWith(
      expect.objectContaining({ finetune_id: 'dinov2-small-segmentation', dataset_ids: ['d1'], recipe_id: 'r1', options: { unfreeze_blocks: 4 } }),
    );
  });
});

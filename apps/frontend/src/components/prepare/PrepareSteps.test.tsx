import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { DatasetAudit, PrepTarget } from '../../api/prep';
import type { AugmentationPlan, BalancePlan } from '../../api/prepPlan';
import type { PrepareData } from '../../hooks/usePrepareData';
import { PrepareSteps, statusesFor } from './PrepareSteps';

vi.mock('../../api/prepPlan', async () => {
  const actual = await vi.importActual<typeof import('../../api/prepPlan')>('../../api/prepPlan');
  return { ...actual, saveRecipe: vi.fn(), previewInput: vi.fn(), previewAugmentation: vi.fn() };
});
const prepPlan = await import('../../api/prepPlan');

const TARGET: PrepTarget = {
  id: 'head-detection-dinov2',
  label: 'Detection head on DINOv2',
  task: 'detection',
  annotation_kind: 'boxes',
  input_size: 448,
  min_visible_px: 28,
};

function audit(target = TARGET.id): DatasetAudit {
  return {
    dataset_id: 'd',
    target,
    created_at: '2026-09-30T10:00:00+00:00',
    summary: { images: 40, annotations: 90, classes: { rbc: 80, platelets: 10 }, problems: 0, warnings: 1 },
    findings: [],
    copy_groups: [],
    unreadable: [],
    excluded: 0,
  };
}

function data(overrides: Partial<PrepareData> = {}): PrepareData {
  return {
    audit: null,
    auditing: null,
    state: { excluded: [], class_map: {} },
    split: null,
    recipes: [],
    busy: false,
    error: '',
    runAudit: vi.fn(),
    fix: vi.fn(async () => 0),
    split_: vi.fn(async () => undefined),
    reloadRecipes: vi.fn(),
    ...overrides,
  };
}

const BALANCE: BalancePlan = {
  ratio: 8,
  recommended: 'weighted-loss',
  reason: 'Classes differ by 8×.',
  classes: [{ name: 'platelets', examples: 10, images: 10, weight: 1.5, repeat: 2 }],
  options: [
    { id: 'none', title: 'Leave it', explained: 'As it is.' },
    { id: 'weighted-loss', title: 'Make rare classes count more', explained: 'Costs more.' },
    { id: 'balanced-sampling', title: 'Show rare classes more often', explained: 'Repeats.' },
  ],
  warnings: [],
  applies_to_training: true,
};

const AUGMENT: AugmentationPlan = {
  recommended: 'microscopy',
  reason: 'A guess from the class names.',
  presets: [
    { id: 'none', title: 'No changes', explained: '', guarded: false },
    { id: 'microscopy', title: 'Microscopy', explained: '', guarded: false },
  ],
  guarded_classes: [],
  applies_to_training: true,
};

function steps(prepare: PrepareData, plans: { balance: BalancePlan | null; augmentation: AugmentationPlan | null }) {
  return (
    <PrepareSteps
      datasetId="d"
      datasetName="Blood cells"
      target={TARGET}
      data={prepare}
      plans={plans}
      choices={{ key: 'd:head-detection-dinov2' }}
      onChoose={vi.fn()}
    />
  );
}

describe('the flow opens where the work is', () => {
  it('starts at the audit, then the split, then saving', () => {
    expect(statusesFor(data(), TARGET.id).audit).toBe('open');
    const audited = statusesFor(data({ audit: audit() }), TARGET.id);
    expect([audited.audit, audited.fix, audited.split]).toEqual(['done', 'done', 'open']);
    // An audit made for another model is not this model's audit.
    expect(statusesFor(data({ audit: audit('rf-detr-nano') }), TARGET.id).audit).toBe('open');
  });
});

describe('recommendations arrive after the first render', () => {
  it('pre-selects the recommendation once it loads, and saves it', async () => {
    const user = userEvent.setup();
    vi.mocked(prepPlan.saveRecipe).mockResolvedValue({ recipe: {} as never, out_of_date: [] });
    const loaded = data({ audit: audit(), split: { mode: 'auto', seed: 42, groups: 1, largest_group: 1, sides: {} as never, buffer: 0, warnings: [] } });
    // Empty first, as a real load produces, then the plans.
    const { rerender } = render(steps(loaded, { balance: null, augmentation: null }));
    rerender(steps(loaded, { balance: BALANCE, augmentation: AUGMENT }));

    await user.click(screen.getByRole('button', { name: /Unequal classes/ }));
    expect(screen.getByRole('radio', { name: /Make rare classes count more/ })).toBeChecked();

    await user.click(screen.getByRole('button', { name: /Save the recipe/ }));
    expect(screen.getByRole('textbox', { name: 'Recipe name' })).toHaveValue('Blood cells for Detection head on DINOv2');
    await user.click(screen.getByRole('button', { name: 'Save the recipe' }));
    expect(prepPlan.saveRecipe).toHaveBeenCalledWith('d', {
      name: 'Blood cells for Detection head on DINOv2',
      target: TARGET.id,
      imbalance: 'weighted-loss',
      augmentation: 'microscopy',
      grid: null,
    });
  });

  it('shows the server’s reason when a step is missing', async () => {
    const user = userEvent.setup();
    vi.mocked(prepPlan.saveRecipe).mockRejectedValue(new Error('Run the Split step first.'));
    render(steps(data({ audit: audit() }), { balance: BALANCE, augmentation: AUGMENT }));
    await user.click(screen.getByRole('button', { name: /Save the recipe/ }));
    await user.click(screen.getByRole('button', { name: 'Save the recipe' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Run the Split step first.');
  });
});

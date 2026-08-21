/**
 * The Dataset Generator proposing with a general detector (doc 42).
 *
 * A separate file because `GeneratorSetup.test.tsx` crossed the 300-line gate, and because
 * `vi.mock` is per-module — the mock declarations cannot move to a shared testkit, so the
 * split is along the describe rather than the fixtures.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { HeadInstanceInfo } from '../api/headInstances';
import { GeneratorSetup } from './GeneratorSetup';


vi.mock('../api/headInstances', async () => {
  const actual = await vi.importActual<typeof import('../api/headInstances')>(
    '../api/headInstances',
  );
  return { ...actual, listHeadInstances: vi.fn() };
});

vi.mock('../api/annotators', async () => {
  const actual = await vi.importActual<typeof import('../api/annotators')>('../api/annotators');
  return { ...actual, listAnnotators: vi.fn() };
});

vi.mock('../api/datasets', async () => {
  const actual = await vi.importActual<typeof import('../api/datasets')>('../api/datasets');
  return { ...actual, listDatasets: vi.fn(), createDataset: vi.fn() };
});

vi.mock('../api/foundation', async () => {
  const actual = await vi.importActual<typeof import('../api/foundation')>('../api/foundation');
  return { ...actual, listFoundations: vi.fn() };
});

vi.mock('../hooks/useTrainerOptions', async () => {
  const actual = await vi.importActual<typeof import('../hooks/useTrainerOptions')>(
    '../hooks/useTrainerOptions',
  );
  return { ...actual, useTrainerOptions: vi.fn() };
});

const headsApi = await import('../api/headInstances');
const options = await import('../hooks/useTrainerOptions');
const datasetsApi = await import('../api/datasets');
const annotatorsApi = await import('../api/annotators');
const foundationApi = await import('../api/foundation');


const DETECTOR: HeadInstanceInfo = {
  id: 'h1',
  name: 'Bolt finder',
  summary: 'Object detection · 2 classes',
  kind: 'trained-here',
  head_type_id: 'dense-detector',
  task: 'detection',
  render_hint: 'boxes',
  backbone_id: 'dinov2-small',
  backbone_family: 'dinov2',
  embed_dim: 384,
  num_classes: 2,
  class_names: ['bolt', 'nut'],
  dataset_ids: ['d1'],
  metrics: {},
  primary_metric: null,
  primary_metric_value: null,
  epochs_trained: 5,
  best_epoch: 4,
  source_repo: null,
  created_at: '2026-08-20T00:00:00+00:00',
};

beforeEach(() => {
  vi.mocked(foundationApi.listFoundations).mockResolvedValue([]);
  vi.mocked(headsApi.listHeadInstances).mockResolvedValue([DETECTOR]);
  vi.mocked(datasetsApi.listDatasets).mockResolvedValue([]);
  vi.mocked(datasetsApi.createDataset).mockResolvedValue({ id: 'new' } as never);
  vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([]);
  vi.mocked(options.useTrainerOptions).mockReturnValue({
    backbones: [{ id: 'dinov2-small', installed: true }],
    loading: false,
    error: null,
  } as never);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('proposing with a general detector (doc 42)', () => {
  const RF_DETR = {
    id: 'rf-detr-nano',
    title: 'RF-DETR (nano)',
    description: 'General object detection, 91 COCO classes.',
    task: 'detection',
    render_hint: 'boxes' as const,
    model_id: 'rf-detr-nano',
    licence: 'Apache-2.0',
    non_commercial: false,
    installed: true,
    approx_size_mb: 116,
    takes_concept: false,
  };

  it('offers it, and it leads the list', async () => {
    vi.mocked(foundationApi.listFoundations).mockResolvedValue([RF_DETR]);
    render(<GeneratorSetup onStart={vi.fn()} />);

    const modes = await screen.findAllByRole('radio', { name: /detector|head you trained|Grounded SAM/ });
    expect(modes[0]).toHaveAccessibleName(/general detector/);
  });

  it('does not select it by default', async () => {
    // Deliberate: someone with trained heads and no detector installed would otherwise
    // land on an empty state telling them to visit Admin. Position, not selection, is
    // where the discoverability lives.
    vi.mocked(foundationApi.listFoundations).mockResolvedValue([RF_DETR]);
    render(<GeneratorSetup onStart={vi.fn()} />);

    expect(await screen.findByRole('radio', { name: /general detector/ })).not.toBeChecked();
  });

  it('emits a foundation config with no backbone', async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    vi.mocked(foundationApi.listFoundations).mockResolvedValue([RF_DETR]);
    render(<GeneratorSetup onStart={onStart} />);

    await user.click(await screen.findByRole('radio', { name: /general detector/ }));
    await user.type(screen.getByPlaceholderText('/Users/you/new-photos'), '/pics');
    await user.type(screen.getByPlaceholderText('Bolts, round two'), 'Things');
    await user.click(screen.getByRole('button', { name: /Start generating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    const config = onStart.mock.calls[0]?.[0];
    expect(config).toMatchObject({ kind: 'foundation', foundationId: 'rf-detr-nano' });
    expect(config).not.toHaveProperty('backboneId');
  });

  it('tells the user where to get one when none is installed', async () => {
    vi.mocked(foundationApi.listFoundations).mockResolvedValue([
      { ...RF_DETR, installed: false },
    ]);
    const user = userEvent.setup();
    render(<GeneratorSetup onStart={vi.fn()} />);

    await user.click(await screen.findByRole('radio', { name: /general detector/ }));

    expect(await screen.findByRole('status')).toHaveTextContent(/Admin \/ Models/);
  });
});

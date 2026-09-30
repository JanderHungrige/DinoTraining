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
  class_names: [],
  dataset_ids: [],
  metrics: {},
  primary_metric: null,
  primary_metric_value: null,
  epochs_trained: 1,
  best_epoch: null,
  source_repo: null,
  created_at: '2026-08-19T00:00:00+00:00',
};

function trainerOptions(overrides: Record<string, unknown> = {}) {
  return {
    datasets: [],
    backbones: [
      { id: 'dinov2-small', installed: true },
      { id: 'dinov2-base', installed: false },
    ],
    headTypes: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
    ...overrides,
  } as unknown as ReturnType<typeof options.useTrainerOptions>;
}

beforeEach(() => {
  // Default: no foundation model offered. Every test that cares sets its own.
  vi.mocked(foundationApi.listFoundations).mockResolvedValue([]);
  vi.mocked(headsApi.listHeadInstances).mockResolvedValue([DETECTOR]);
  vi.mocked(datasetsApi.listDatasets).mockResolvedValue([
    { id: 'd1', name: 'Bolts', counts: { images: 3 } } as never,
  ]);
  vi.mocked(datasetsApi.createDataset).mockResolvedValue({ id: 'new-1' } as never);
  vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
    { id: 'grounded-sam', name: 'Grounded SAM', ready: true } as never,
  ]);
  vi.mocked(options.useTrainerOptions).mockReturnValue(trainerOptions());
});

afterEach(() => vi.clearAllMocks());

describe('GeneratorSetup remembers its entries (doc 69)', () => {
  it('keeps the folder, mode, concept and threshold across an unmount — a tab switch', async () => {
    const user = userEvent.setup();
    const first = render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    await user.type(screen.getByLabelText(/image folder/i), '/data/rail');
    await user.type(screen.getByLabelText(/^concept$/i), 'a signal');
    first.unmount();

    render(<GeneratorSetup onStart={vi.fn()} />);
    expect(screen.getByRole('radio', { name: /Grounded SAM/ })).toBeChecked();
    expect(screen.getByLabelText(/image folder/i)).toHaveValue('/data/rail');
    expect(screen.getByLabelText(/^concept$/i)).toHaveValue('a signal');
  });

  it('does not write into a remembered dataset that has since been deleted', async () => {
    // Remembered from an earlier session; the list no longer offers it.
    localStorage.setItem('dinotraining.v1.generator.dataset', '"deleted-7"');
    localStorage.setItem('dinotraining.v1.generator.mode', '"masks"');
    localStorage.setItem('dinotraining.v1.generator.concept', '"a bolt"');
    localStorage.setItem(
      'dinotraining.v1.generator.source',
      '{"kind":"folder","folder":"/photos"}',
    );
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Grounded SAM/ });

    // Falls back to "a new dataset", which needs a name — so Start waits for one rather
    // than submitting an id the backend no longer has.
    expect(screen.getByLabelText(/save into/i)).not.toHaveValue('deleted-7');
    expect(screen.getByRole('button', { name: /start generating/i })).toBeDisabled();
  });

  it('remembers the dataset it created, not the name that created it', async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    const first = render(<GeneratorSetup onStart={onStart} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    await user.type(screen.getByLabelText(/new dataset name/i), 'Rail run 1');
    await user.click(screen.getByRole('button', { name: /start generating/i }));
    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith(expect.objectContaining({ datasetId: 'new-1' })),
    );
    first.unmount();

    // The next mount lists the dataset that was created.
    vi.mocked(datasetsApi.listDatasets).mockResolvedValue([
      { id: 'd1', name: 'Bolts', counts: { images: 3 } } as never,
      { id: 'new-1', name: 'Rail run 1', counts: { images: 0 } } as never,
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await waitFor(() => expect(screen.getByLabelText(/save into/i)).toHaveValue('new-1'));
    // A remembered name would have created a second "Rail run 1" on the next start.
    expect(screen.queryByLabelText(/new dataset name/i)).not.toBeInTheDocument();
    expect(vi.mocked(datasetsApi.createDataset)).toHaveBeenCalledTimes(1);
  });
});

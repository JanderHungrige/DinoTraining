/**
 * The annotator choice in the generator's setup form.
 *
 * Split from GeneratorSetup.test.tsx at the 300-line limit. Which annotator runs is its
 * own question — it is about what is *installed*, not about how the form is filled in.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { HeadInstanceInfo } from '../api/headInstances';
import { GeneratorSetup } from './GeneratorSetup';

vi.mock('../api/annotators', async () => {
  const actual = await vi.importActual<typeof import('../api/annotators')>('../api/annotators');
  return { ...actual, listAnnotators: vi.fn() };
});
vi.mock('../api/headInstances', async () => {
  const actual = await vi.importActual<typeof import('../api/headInstances')>(
    '../api/headInstances',
  );
  return { ...actual, listHeadInstances: vi.fn() };
});
vi.mock('../api/datasets', async () => {
  const actual = await vi.importActual<typeof import('../api/datasets')>('../api/datasets');
  return { ...actual, listDatasets: vi.fn(), createDataset: vi.fn() };
});
vi.mock('../hooks/useTrainerOptions', async () => {
  const actual = await vi.importActual<typeof import('../hooks/useTrainerOptions')>(
    '../hooks/useTrainerOptions',
  );
  return { ...actual, useTrainerOptions: vi.fn() };
});

const annotatorsApi = await import('../api/annotators');
const headsApi = await import('../api/headInstances');
const datasetsApi = await import('../api/datasets');
const options = await import('../hooks/useTrainerOptions');

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

beforeEach(() => {
  vi.mocked(headsApi.listHeadInstances).mockResolvedValue([DETECTOR]);
  vi.mocked(datasetsApi.listDatasets).mockResolvedValue([
    { id: 'd1', name: 'Bolts', counts: { images: 3 } } as never,
  ]);
  vi.mocked(datasetsApi.createDataset).mockResolvedValue({ id: 'new-1' } as never);
  vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
    { id: 'grounded-sam', name: 'Grounded SAM', ready: true } as never,
  ]);
  vi.mocked(options.useTrainerOptions).mockReturnValue({
    datasets: [],
    backbones: [{ id: 'dinov2-small', installed: true }],
    headTypes: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
  } as unknown as ReturnType<typeof options.useTrainerOptions>);
});

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe('GeneratorSetup — annotator choice', () => {
  it('hides the annotator picker when only one is installed', async () => {
    const user = userEvent.setup();
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    expect(screen.queryByLabelText(/^annotator$/i)).not.toBeInTheDocument();
  });

  it('offers SAM 3 once it is installed', async () => {
    // Not before: 3.2 GB behind a manual approval, and the admin tab is where it is got.
    const user = userEvent.setup();
    vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
      { id: 'grounded-sam', name: 'Grounded SAM', ready: true } as never,
      { id: 'sam3', name: 'SAM 3', ready: true, description: 'Concept-prompted.' } as never,
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    const picker = await screen.findByLabelText(/^annotator$/i);
    expect([...picker.querySelectorAll('option')].map((o) => o.value)).toEqual([
      'grounded-sam',
      'sam3',
    ]);
  });

  it('does not offer an annotator whose models are not downloaded', async () => {
    const user = userEvent.setup();
    vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
      { id: 'grounded-sam', name: 'Grounded SAM', ready: true } as never,
      { id: 'sam3', name: 'SAM 3', ready: false } as never,
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    expect(screen.queryByLabelText(/^annotator$/i)).not.toBeInTheDocument();
  });

  it('starts with the chosen annotator', async () => {
    const user = userEvent.setup();
    vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
      { id: 'grounded-sam', name: 'Grounded SAM', ready: true } as never,
      { id: 'sam3', name: 'SAM 3', ready: true } as never,
    ]);
    const onStart = vi.fn();
    render(<GeneratorSetup onStart={onStart} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    await user.selectOptions(await screen.findByLabelText(/^annotator$/i), 'sam3');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    await user.type(screen.getByLabelText(/^concept$/i), 'a bolt');
    await user.click(screen.getByRole('button', { name: /start generating/i }));

    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith(
        expect.objectContaining({ kind: 'masks', annotatorId: 'sam3' }),
      ),
    );
  });
});

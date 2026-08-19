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

describe('GeneratorSetup', () => {
  it('offers the ungated mask path without any head', async () => {
    // Grounded SAM needs no trained head at all, so it must be reachable even on an
    // install where nothing can propose boxes.
    const user = userEvent.setup();
    vi.mocked(headsApi.listHeadInstances).mockResolvedValue([]);
    const onStart = vi.fn();
    render(<GeneratorSetup onStart={onStart} />);
    await screen.findByRole('status');

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    await user.type(screen.getByLabelText(/^concept$/i), 'a bolt');
    await user.click(screen.getByRole('button', { name: /start generating/i }));

    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith(
        expect.objectContaining({ kind: 'masks', concept: 'a bolt', datasetId: 'd1' }),
      ),
    );
  });

  it('will not start the mask path without a concept', async () => {
    const user = userEvent.setup();
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');

    expect(screen.getByRole('button', { name: /start generating/i })).toBeDisabled();
  });

  it('hides the head picker in mask mode', async () => {
    const user = userEvent.setup();
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    expect(screen.queryByRole('radio', { name: /Bolt finder/ })).not.toBeInTheDocument();
  });

  it('offers only installed backbones', async () => {
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    // Scoped to the backbone select: the form has a dataset select too, and an
    // unscoped option query would silently start asserting about the wrong control.
    const backbone = screen.getByLabelText(/^backbone$/i);
    const values = [...backbone.querySelectorAll('option')].map((o) => o.value);
    expect(values).toEqual(['dinov2-small']);
  });

  it('keeps Start disabled until a folder is typed', async () => {
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    expect(screen.getByRole('button', { name: /start generating/i })).toBeDisabled();
  });

  it('enables Start once every field has an effective value', async () => {
    const user = userEvent.setup();
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    expect(screen.getByRole('button', { name: /start generating/i })).toBeEnabled();
  });

  it('starts with the derived defaults without the user touching them', async () => {
    // The CLAUDE.md trap: seeding state from async lists leaves it at '' while the
    // controls render their first option anyway, so Start submits empty ids — or stays
    // disabled forever. Nothing here is touched except the folder.
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<GeneratorSetup onStart={onStart} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    await user.click(screen.getByRole('button', { name: /start generating/i }));

    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith(
        expect.objectContaining({
          folder: '/photos',
          backboneId: 'dinov2-small',
          instanceId: 'h1',
          datasetId: 'd1',
        }),
      ),
    );
  });

  it('does not offer a head that cannot produce boxes', async () => {
    vi.mocked(headsApi.listHeadInstances).mockResolvedValue([
      { ...DETECTOR, id: 'seg', name: 'Segmenter', render_hint: 'masks' },
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);

    expect(await screen.findByRole('status')).toHaveTextContent(/Head Trainer/);
    // Scoped to the head radios: the mode switch is also a radio group, and an
    // unscoped query would pass for the wrong reason once anything else is added.
    expect(screen.queryByRole('radio', { name: /Segmenter/ })).not.toBeInTheDocument();
  });

  it('cannot start when no head is eligible', async () => {
    const user = userEvent.setup();
    vi.mocked(headsApi.listHeadInstances).mockResolvedValue([]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('status');

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    expect(screen.getByRole('button', { name: /start generating/i })).toBeDisabled();
  });

  it('passes the chosen threshold through', async () => {
    const user = userEvent.setup();
    const onStart = vi.fn();
    render(<GeneratorSetup onStart={onStart} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    await user.click(screen.getByRole('button', { name: /start generating/i }));

    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith(
        expect.objectContaining({ scoreThreshold: expect.any(Number) }),
      ),
    );
  });

  it('survives heads arriving after the first render', async () => {
    // The sequence a real load produces: render with nothing, then data lands.
    let resolve: (value: HeadInstanceInfo[]) => void = () => {};
    vi.mocked(headsApi.listHeadInstances).mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );

    render(<GeneratorSetup onStart={vi.fn()} />);
    expect(screen.getByRole('status')).toHaveTextContent(/Loading heads/);

    resolve([DETECTOR]);
    await waitFor(() =>
      expect(screen.getByRole('radio', { name: /Bolt finder/ })).toBeInTheDocument(),
    );
  });
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

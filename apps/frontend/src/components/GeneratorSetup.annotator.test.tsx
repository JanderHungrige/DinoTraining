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

const annotatorsApi = await import('../api/annotators');
const headsApi = await import('../api/headInstances');
const datasetsApi = await import('../api/datasets');
const options = await import('../hooks/useTrainerOptions');
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

beforeEach(() => {
  // Default: no foundation models. The tests below that care about them say so.
  vi.mocked(foundationApi.listFoundations).mockResolvedValue([]);
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

  it('tells the user SAM 3 takes one concept at a time', async () => {
    // Verified against real weights: "a red circle. a blue square." given to SAM 3 as one
    // prompt returns a single mask at score 0.372, while the same two phrases run
    // separately score 0.977 and 0.968. Grounded SAM handles the joined form correctly,
    // so the guidance has to differ per annotator or it is wrong for one of them.
    const user = userEvent.setup();
    vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
      { id: 'grounded-sam', name: 'Grounded SAM', ready: true, prompt_style: 'phrases' } as never,
      { id: 'sam3', name: 'SAM 3', ready: true, prompt_style: 'concept' } as never,
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    expect(screen.getByLabelText(/^concept$/i)).toHaveAttribute('placeholder', 'a bolt. a nut.');
    expect(screen.getByText(/several phrases separated by full stops/i)).toBeInTheDocument();

    await user.selectOptions(await screen.findByLabelText(/^annotator$/i), 'sam3');
    expect(screen.getByLabelText(/^concept$/i)).toHaveAttribute('placeholder', 'a bolt');
    expect(screen.getByText(/one concept at a time/i)).toBeInTheDocument();
  });

  it('keeps the multi-phrase guidance on every Grounded SAM size', async () => {
    // The guidance used to come from `annotatorId === 'grounded-sam'`, which was right for
    // exactly one row. The bigger tiers are the same pipeline and take the same prompts, so
    // an id comparison would have told the user to run phrases one at a time for no reason.
    const user = userEvent.setup();
    vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
      { id: 'grounded-sam', name: 'Grounded SAM (fast)', ready: true, prompt_style: 'phrases' } as never,
      { id: 'grounded-sam-large', name: 'Grounded SAM (large)', ready: true, prompt_style: 'phrases' } as never,
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    await user.selectOptions(await screen.findByLabelText(/^annotator$/i), 'grounded-sam-large');

    expect(screen.getByLabelText(/^concept$/i)).toHaveAttribute('placeholder', 'a bolt. a nut.');
    expect(screen.getByText(/several phrases separated by full stops/i)).toBeInTheDocument();
  });

  it('starts the size that was chosen, not the default one', async () => {
    // The whole point of the tiers: picking `large` must run large. Nothing downstream
    // would notice if it silently ran the 834 MB pipeline instead.
    const user = userEvent.setup();
    vi.mocked(annotatorsApi.listAnnotators).mockResolvedValue([
      { id: 'grounded-sam', name: 'Grounded SAM (fast)', ready: true, prompt_style: 'phrases' } as never,
      { id: 'grounded-sam-base', name: 'Grounded SAM (base)', ready: true, prompt_style: 'phrases' } as never,
    ]);
    const onStart = vi.fn();
    render(<GeneratorSetup onStart={onStart} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
    await user.selectOptions(await screen.findByLabelText(/^annotator$/i), 'grounded-sam-base');
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    await user.type(screen.getByLabelText(/^concept$/i), 'a bolt');
    await user.click(screen.getByRole('button', { name: /start generating/i }));

    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith(
        expect.objectContaining({ kind: 'masks', annotatorId: 'grounded-sam-base' }),
      ),
    );
  });
});

describe('a prompted detector in foundation mode (doc 66)', () => {
  /**
   * Two reports, one cause. "Grounding DINO is not available in the Dataset Generator"
   * and "choosing a concept model like SAM 3 does not open the concept line".
   *
   * `FoundationPicker` filters with `proposesBoxes`, so SAM 3 was already *listed* here —
   * but the Generator mounted the picker without an `onConceptChange`, so the field never
   * appeared, and its own `usableDetectors` filtered by `render_hint === 'boxes'`, a
   * narrower list than the one on screen. Selectable, unpromptable, and the ready gate
   * reasoning about a different set of models than the user could see.
   */
  function withDetectors(entries: unknown[]): void {
    vi.mocked(foundationApi.listFoundations).mockResolvedValue(entries as never);
  }

  it('shows the prompt field for a prompted detector', async () => {
    const user = userEvent.setup();
    withDetectors([
      {
        id: 'grounding-dino-tiny',
        title: 'Grounding DINO (tiny)',
        render_hint: 'boxes',
        installed: true,
        takes_concept: true,
      },
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /general detector/i }));

    expect(await screen.findByLabelText(/what to find/i)).toBeInTheDocument();
  });

  it('shows it for a mask model listed as a detector too', async () => {
    // SAM 3 reports `masks` but proposes boxes on the way there, which is why it is in
    // this list at all — and exactly the case that had no prompt field.
    const user = userEvent.setup();
    withDetectors([
      { id: 'sam3', title: 'SAM 3', render_hint: 'masks', installed: true, takes_concept: true },
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /general detector/i }));

    expect(await screen.findByRole('radio', { name: /SAM 3/ })).toBeInTheDocument();
    expect(screen.getByLabelText(/what to find/i)).toBeInTheDocument();
  });

  it('shows no prompt field for RF-DETR, which ignores one', async () => {
    const user = userEvent.setup();
    withDetectors([
      {
        id: 'rf-detr-nano',
        title: 'RF-DETR (nano)',
        render_hint: 'boxes',
        installed: true,
        takes_concept: false,
      },
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.click(screen.getByRole('radio', { name: /general detector/i }));

    expect(screen.queryByLabelText(/what to find/i)).not.toBeInTheDocument();
  });

  it('refuses to start a prompted detector with no prompt', async () => {
    // It would run, succeed, and return nothing — the same shape as "found nothing here".
    const user = userEvent.setup();
    withDetectors([
      {
        id: 'grounding-dino-tiny',
        title: 'Grounding DINO (tiny)',
        render_hint: 'boxes',
        installed: true,
        takes_concept: true,
      },
    ]);
    render(<GeneratorSetup onStart={vi.fn()} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.click(screen.getByRole('radio', { name: /general detector/i }));
    await user.type(screen.getByLabelText(/image folder/i), '/photos');

    expect(screen.getByRole('button', { name: /start generating/i })).toBeDisabled();
  });

  it('starts with the prompt once one is typed', async () => {
    const user = userEvent.setup();
    withDetectors([
      {
        id: 'grounding-dino-tiny',
        title: 'Grounding DINO (tiny)',
        render_hint: 'boxes',
        installed: true,
        takes_concept: true,
      },
    ]);
    const onStart = vi.fn();
    render(<GeneratorSetup onStart={onStart} />);
    await screen.findByRole('radio', { name: /Bolt finder/ });

    await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
    await user.click(screen.getByRole('radio', { name: /general detector/i }));
    await user.type(screen.getByLabelText(/image folder/i), '/photos');
    await user.type(await screen.findByLabelText(/what to find/i), 'a bolt');
    await user.click(screen.getByRole('button', { name: /start generating/i }));

    await waitFor(() =>
      expect(onStart).toHaveBeenCalledWith(
        expect.objectContaining({
          kind: 'foundation',
          foundationId: 'grounding-dino-tiny',
          concept: 'a bolt',
        }),
      ),
    );
  });
});

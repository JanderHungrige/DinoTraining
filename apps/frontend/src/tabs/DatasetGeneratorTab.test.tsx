import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';

import { DatasetGeneratorTab } from './DatasetGeneratorTab';

vi.mock('../api/annotate', async () => {
  const actual = await vi.importActual<typeof import('../api/annotate')>('../api/annotate');
  return { ...actual, listFolderImages: vi.fn(), imageUrl: (p: string) => `/img?${p}` };
});
vi.mock('../api/generate', async () => {
  const actual = await vi.importActual<typeof import('../api/generate')>('../api/generate');
  return { ...actual, proposeMasks: vi.fn(), proposeWithExpertHead: vi.fn() };
});
vi.mock('../api/headInstances', async () => {
  const actual = await vi.importActual<typeof import('../api/headInstances')>(
    '../api/headInstances',
  );
  return { ...actual, listHeadInstances: vi.fn() };
});
vi.mock('../api/datasets', async () => {
  const actual = await vi.importActual<typeof import('../api/datasets')>('../api/datasets');
  return { ...actual, listDatasets: vi.fn(), createDataset: vi.fn(), saveImageMasks: vi.fn() };
});

vi.mock('../hooks/useTrainerOptions', async () => {
  const actual = await vi.importActual<typeof import('../hooks/useTrainerOptions')>(
    '../hooks/useTrainerOptions',
  );
  return { ...actual, useTrainerOptions: vi.fn() };
});

const annotate = await import('../api/annotate');
const generate = await import('../api/generate');
const headsApi = await import('../api/headInstances');
const options = await import('../hooks/useTrainerOptions');
const datasetsApi = await import('../api/datasets');

const MASK_RESPONSE = {
  image_path: '/photos/a.png',
  width: 400,
  height: 300,
  device: 'mps',
  annotator_id: 'grounded-sam',
  annotator_name: 'Grounded SAM (Grounding DINO + SAM 2.1)',
  masks: [
    {
      label: 'positive' as const,
      provenance: 'grounded-sam' as const,
      rle: { size: [300, 400] as [number, number], counts: [0, 120000] },
      x: 10,
      y: 20,
      w: 100,
      h: 50,
      score: 0.88,
      concept: 'a red circle',
      producer: { id: 'grounded-sam', label: 'Grounded SAM', concept: 'a red circle' },
      mask_png: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    },
  ],
};

let consoleError: MockInstance<(...args: unknown[]) => void>;

beforeEach(() => {
  vi.mocked(annotate.listFolderImages).mockResolvedValue(['/photos/a.png']);
  vi.mocked(generate.proposeMasks).mockResolvedValue(MASK_RESPONSE);
  vi.mocked(headsApi.listHeadInstances).mockResolvedValue([]);
  vi.mocked(datasetsApi.listDatasets).mockResolvedValue([
    { id: 'd1', name: 'Bolts', counts: { images: 0 } } as never,
  ]);
  vi.mocked(datasetsApi.saveImageMasks).mockResolvedValue({
    images: 1, boxes: 0, masks: 1, positive: 1, negative: 0, unclear: 0,
  });
  vi.mocked(options.useTrainerOptions).mockReturnValue({
    datasets: [],
    backbones: [{ id: 'dinov2-small', installed: true }],
    headTypes: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
  } as unknown as ReturnType<typeof options.useTrainerOptions>);
  consoleError = vi.spyOn(console, 'error').mockImplementation(() => {}) as unknown as
    MockInstance<(...args: unknown[]) => void>;
});

afterEach(() => {
  // clearAllMocks as well as restoreAllMocks: restore undoes spies, but leaves the call
  // history of vi.fn() mocks intact, so `mock.calls[0]` silently belongs to an earlier
  // test. That is exactly how this file first "proved" the reviewer's verdict was lost.
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

async function startMaskSession(): Promise<void> {
  const user = userEvent.setup();
  render(<DatasetGeneratorTab />);
  await screen.findByRole('status');

  await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
  await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
  await user.type(screen.getByLabelText(/image folder/i), '/photos');
  await user.type(screen.getByLabelText(/^concept$/i), 'a red circle');
  await user.click(screen.getByRole('button', { name: /start generating/i }));
  await screen.findByRole('button', { name: /propose masks/i });
}

describe('DatasetGeneratorTab', () => {
  it('reaches the mask review surface and proposes', async () => {
    const user = userEvent.setup();
    await startMaskSession();

    await user.click(screen.getByRole('button', { name: /propose masks/i }));

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Positive mask: a red circle/ })).toBeInTheDocument(),
    );
  });

  it('does not violate the Rules of Hooks across a config change', async () => {
    // The tab swaps between a setup form, a box canvas and a mask canvas. React only
    // reports a hook-order violation at runtime, and a dev-server console carries stale
    // messages across reloads — so the honest check is a fresh render here.
    await startMaskSession();

    const hookErrors = consoleError.mock.calls.filter((call: unknown[]) =>
      String(call[0]).includes('order of Hooks'),
    );
    expect(hookErrors).toEqual([]);
  });

  it('renders no React errors or warnings at all on this path', async () => {
    await startMaskSession();
    expect(consoleError.mock.calls).toEqual([]);
  });

  it('names the annotator that produced the masks', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /propose masks/i }));

    await waitFor(() => expect(screen.getByText(/Grounded SAM/)).toBeInTheDocument());
  });

  it('cannot save before anything has been proposed', async () => {
    await startMaskSession();
    expect(screen.getByRole('button', { name: /save to dataset/i })).toBeDisabled();
  });

  it('saves reviewed masks into the chosen dataset', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /propose masks/i }));
    await screen.findByRole('button', { name: /Positive mask/ });

    await user.click(screen.getByRole('button', { name: /save to dataset/i }));

    await waitFor(() => expect(datasetsApi.saveImageMasks).toHaveBeenCalled());
    const [datasetId] = vi.mocked(datasetsApi.saveImageMasks).mock.calls[0]!;
    expect(datasetId).toBe('d1');
  });

  it('saves the reviewer verdict, not the proposed one', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /propose masks/i }));

    // Cycle the mask from positive to negative before saving.
    await user.click(await screen.findByRole('button', { name: /Positive mask/ }));
    // Confirm the cycle actually landed before blaming the save path.
    await screen.findByRole('button', { name: /Negative mask/ });
    await user.click(screen.getByRole('button', { name: /save to dataset/i }));

    await waitFor(() => expect(datasetsApi.saveImageMasks).toHaveBeenCalled());
    const reviewed = vi.mocked(datasetsApi.saveImageMasks).mock.calls[0]![2];
    expect(reviewed[0]?.label).toBe('negative');
  });

  it('clears the unsaved marker once written', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /propose masks/i }));
    await screen.findByRole('button', { name: /Positive mask/ });
    expect(screen.getByText(/unsaved changes/i)).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: /save to dataset/i }));
    await waitFor(() =>
      expect(screen.queryByText(/unsaved changes/i)).not.toBeInTheDocument(),
    );
  });
});

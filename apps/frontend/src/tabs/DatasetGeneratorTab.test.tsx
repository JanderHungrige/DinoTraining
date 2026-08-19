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
      mask_png: 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==',
    },
  ],
};

let consoleError: MockInstance<(...args: unknown[]) => void>;

beforeEach(() => {
  vi.mocked(annotate.listFolderImages).mockResolvedValue(['/photos/a.png']);
  vi.mocked(generate.proposeMasks).mockResolvedValue(MASK_RESPONSE);
  vi.mocked(headsApi.listHeadInstances).mockResolvedValue([]);
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

afterEach(() => vi.restoreAllMocks());

async function startMaskSession(): Promise<void> {
  const user = userEvent.setup();
  render(<DatasetGeneratorTab />);
  await screen.findByRole('status');

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

  it('says saving is not built yet rather than showing a dead button', async () => {
    await startMaskSession();
    expect(screen.queryByRole('button', { name: /^save$/i })).not.toBeInTheDocument();
    expect(screen.getByText(/not saved yet/i)).toBeInTheDocument();
  });
});

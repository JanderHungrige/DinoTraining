import { cleanup, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi, type MockInstance } from 'vitest';

import { DatasetGeneratorTab } from './DatasetGeneratorTab';

/* Doc 71: autoplay through the real tab, with the proposer and the store mocked. */

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
  // These tests drive the manual flow. Auto-propose is on by default (doc 70) and has its
  // own test below; left on here, a proposal would race every "before proposing" check.
  localStorage.setItem('dinotraining.v1.generator.autoPropose', 'false');
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

async function startMaskSession(
  onInspect?: (datasetId: string, sequence: string | null) => void,
): Promise<void> {
  const user = userEvent.setup();
  render(<DatasetGeneratorTab {...(onInspect ? { onInspect } : {})} />);
  await screen.findByRole('status');

  await user.selectOptions(screen.getByLabelText(/save into/i), 'd1');
  await user.click(screen.getByRole('radio', { name: /Grounded SAM/ }));
  await user.type(screen.getByLabelText(/image folder/i), '/photos');
  await user.type(screen.getByLabelText(/^concept$/i), 'a red circle');
  await user.click(screen.getByRole('button', { name: /start generating/i }));
  await screen.findByRole('button', { name: /propose masks/i });
}

function maskFor(path: string) {
  return { ...MASK_RESPONSE, image_path: path };
}

beforeEach(() => {
  vi.mocked(annotate.listFolderImages).mockResolvedValue([
    '/photos/a.png',
    '/photos/b.png',
    '/photos/c.png',
  ]);
  vi.mocked(generate.proposeMasks).mockImplementation(async (request: { imagePath: string }) =>
    maskFor(request.imagePath),
  );
});

describe('DatasetGeneratorTab — autoplay (doc 71)', () => {
  it('proposes, holds and saves every image from the current one to the last', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /next/i }));
    await user.click(screen.getByRole('button', { name: /start analysis/i }));

    expect(await screen.findByRole('button', { name: /stop/i })).toBeInTheDocument();
    await waitFor(
      () => expect(screen.getByText(/reached the last image/)).toBeInTheDocument(),
      { timeout: 4000 },
    );
    // Started at b, not at a: Start begins where the user is.
    const saved = vi.mocked(datasetsApi.saveImageMasks).mock.calls.map(([, p]) => p.image_path);
    expect(saved).toEqual(['/photos/b.png', '/photos/c.png']);
    expect(screen.getByText(/2 saved/)).toBeInTheDocument();
    // A run is many renders driven from outside React's event handlers; none may warn.
    expect(consoleError.mock.calls).toEqual([]);
  });

  it('stops on the image it is holding, without saving it', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    // The first proposal is on screen and being held.
    await screen.findByRole('button', { name: /Positive mask/ });
    await user.click(screen.getByRole('button', { name: /stop/i }));

    expect(await screen.findByText(/stopped here/)).toBeInTheDocument();
    expect(datasetsApi.saveImageMasks).not.toHaveBeenCalled();
    // Left editable, with the proposal the user stopped to correct.
    expect(screen.getByRole('button', { name: /Positive mask/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeEnabled();
  });

  it('in hidden mode shows a percentage instead of the image', async () => {
    const user = userEvent.setup();
    // Slow enough to see the bar: with no hold in hidden mode, instant mocks would finish
    // the whole run before the first assertion looked.
    vi.mocked(generate.proposeMasks).mockImplementation(async (request: { imagePath: string }) => {
      await new Promise((resolve) => setTimeout(resolve, 150));
      return maskFor(request.imagePath);
    });
    await startMaskSession();
    await user.click(screen.getByRole('checkbox', { name: /run hidden/i }));
    await user.click(screen.getByRole('button', { name: /start analysis/i }));

    expect(await screen.findByRole('progressbar', { name: /autoplay progress/i })).toBeInTheDocument();
    // No canvas while hidden: nothing is drawn per image.
    expect(screen.queryByRole('button', { name: /Positive mask/ })).not.toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/reached the last image/)).toBeInTheDocument(), {
      timeout: 3000,
    });
    expect(vi.mocked(datasetsApi.saveImageMasks)).toHaveBeenCalledTimes(3);
  });

  it('stops when the tab is left, instead of running on with nothing on screen', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    await screen.findByRole('button', { name: /Positive mask/ });

    cleanup();
    await new Promise((resolve) => setTimeout(resolve, 1200));
    expect(datasetsApi.saveImageMasks).not.toHaveBeenCalled();
    expect(generate.proposeMasks).toHaveBeenCalledTimes(1);
  });
});

describe('DatasetGeneratorTab — asking when unclear (doc 72)', () => {
  beforeEach(() => {
    // The mocked mask scores 0.88: a band around it makes every image a question.
    localStorage.setItem('dinotraining.v1.generator.askUnclear', 'true');
    localStorage.setItem('dinotraining.v1.generator.unclearBand', '{"low":0.8,"high":0.9}');
  });

  it('pauses, lets the user overrule, and saves their verdict — not the model\'s', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /start analysis/i }));

    const question = await screen.findByRole('alert', { name: /waiting for you/i });
    expect(question).toHaveTextContent('Paused on image 1 of 3');
    expect(datasetsApi.saveImageMasks).not.toHaveBeenCalled();

    // Marked unclear for the question; one click cycles it on to positive.
    const mask = screen.getByRole('button', { name: /Unclear mask/ });
    await user.click(mask);
    expect(screen.getByRole('button', { name: /Positive mask/ })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Continue' }));

    await waitFor(() => expect(datasetsApi.saveImageMasks).toHaveBeenCalled());
    const [, , reviewed] = vi.mocked(datasetsApi.saveImageMasks).mock.calls[0]!;
    expect(reviewed[0]!.label).toBe('positive');
    // And it goes on to ask about the next one.
    expect(await screen.findByText(/Paused on image 2 of 3/)).toBeInTheDocument();
  });

  it('saves an unanswered question as unclear', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    await screen.findByRole('alert', { name: /waiting for you/i });
    await user.click(screen.getByRole('button', { name: 'Continue' }));

    await waitFor(() => expect(datasetsApi.saveImageMasks).toHaveBeenCalled());
    const [, , reviewed] = vi.mocked(datasetsApi.saveImageMasks).mock.calls[0]!;
    expect(reviewed[0]!.label).toBe('unclear');
  });

  it('Stop here ends the run on that image, unsaved', async () => {
    const user = userEvent.setup();
    await startMaskSession();
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    await screen.findByRole('alert', { name: /waiting for you/i });
    await user.click(screen.getByRole('button', { name: /stop here/i }));

    expect(await screen.findByText(/stopped here/)).toBeInTheDocument();
    expect(datasetsApi.saveImageMasks).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /start analysis/i })).toBeEnabled();
  });
});

describe('DatasetGeneratorTab — inspect what I just annotated (doc 74)', () => {
  it('jumps with this run\'s dataset and the folder its frames came from', async () => {
    const user = userEvent.setup();
    const onInspect = vi.fn();
    await startMaskSession(onInspect);
    await user.click(screen.getByRole('button', { name: /inspect what i just annotated/i }));
    expect(onInspect).toHaveBeenCalledWith('d1', '/photos');
  });

  it('is not offered mid-run, where leaving would stop autoplay unasked', async () => {
    const user = userEvent.setup();
    await startMaskSession(vi.fn());
    await user.click(screen.getByRole('button', { name: /start analysis/i }));
    expect(screen.getByRole('button', { name: /inspect what i just annotated/i })).toBeDisabled();
  });
});


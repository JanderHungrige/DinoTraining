import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../api/client';
import type { ExpertProposalResponse } from '../api/generate';
import { useGeneratorSession, type GeneratorConfig } from './useGeneratorSession';

vi.mock('../api/annotate', () => ({ listFolderImages: vi.fn() }));
vi.mock('../api/generate', async () => {
  const actual = await vi.importActual<typeof import('../api/generate')>('../api/generate');
  return { ...actual, proposeWithExpertHead: vi.fn() };
});

const annotate = await import('../api/annotate');
const generate = await import('../api/generate');

const CONFIG: GeneratorConfig = {
  folder: '/photos',
  backboneId: 'dinov2-small',
  instanceId: 'h1',
  scoreThreshold: 0.3,
};

function proposal(overrides: Partial<ExpertProposalResponse> = {}): ExpertProposalResponse {
  return {
    image_path: '/photos/a.png',
    width: 640,
    height: 480,
    device: 'mps',
    head_name: 'Bolt finder',
    head_summary: 'Object detection · 2 classes',
    boxes: [
      {
        label: 'positive',
        provenance: 'expert-head',
        x: 10,
        y: 20,
        w: 30,
        h: 40,
        prompt: 'bolt',
        score: 0.8,
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(annotate.listFolderImages).mockResolvedValue([
    '/photos/a.png',
    '/photos/b.png',
  ]);
  vi.mocked(generate.proposeWithExpertHead).mockResolvedValue(proposal());
});

afterEach(() => vi.clearAllMocks());

describe('useGeneratorSession', () => {
  it('lists the folder and starts at the first image', async () => {
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).toBe('/photos/a.png'));
    expect(result.current.images).toHaveLength(2);
  });

  it('turns proposals into canvas boxes carrying their provenance', async () => {
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.boxes).toHaveLength(1);
    expect(result.current.boxes[0]?.provenance).toBe('expert-head');
    expect(result.current.boxes[0]?.text).toBe('bolt');
  });

  it('records the head by name and summary', async () => {
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());
    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.headName).toBe('Bolt finder');
    expect(result.current.headSummary).toContain('Object detection');
  });

  it('takes the image size from the proposal', async () => {
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());
    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.imageSize).toEqual({ width: 640, height: 480 });
  });

  it('clears boxes when moving to another image', async () => {
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());
    await act(async () => {
      await result.current.propose();
    });
    expect(result.current.boxes).toHaveLength(1);

    act(() => result.current.next());

    expect(result.current.currentImage).toBe('/photos/b.png');
    expect(result.current.boxes).toHaveLength(0);
  });

  it('drops a proposal that lands after the user has moved on', async () => {
    // Without the guard this is a silent mislabel: boxes computed for image A appear
    // over image B, in B's coordinate space, and look entirely plausible.
    let resolveLate: (value: ExpertProposalResponse) => void = () => {};
    vi.mocked(generate.proposeWithExpertHead).mockReturnValue(
      new Promise((resolve) => {
        resolveLate = resolve;
      }),
    );

    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());

    let pending: Promise<void> = Promise.resolve();
    act(() => {
      pending = result.current.propose();
    });
    act(() => result.current.next());

    await act(async () => {
      resolveLate(proposal());
      await pending;
    });

    expect(result.current.currentImage).toBe('/photos/b.png');
    expect(result.current.boxes).toHaveLength(0);
  });

  it("surfaces the backend's own reason for refusing a head", async () => {
    // The 409 from `25-expert-annotator` says what the head predicts and where to run
    // it instead. Replacing that with a generic message throws away the only text that
    // tells the user what to do next.
    vi.mocked(generate.proposeWithExpertHead).mockRejectedValue(
      new ApiError(409, 'conflict', 'Depth head predicts depth-map, which cannot be reviewed as boxes.'),
    );
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.error).toMatch(/cannot be reviewed as boxes/);
    expect(result.current.proposing).toBe(false);
  });

  it('falls back to a readable message for a non-API failure', async () => {
    // A transport or programming error has no server message to show; the user still
    // needs something better than a blank panel.
    vi.mocked(generate.proposeWithExpertHead).mockRejectedValue(new TypeError('boom'));
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.error).toMatch(/could not propose boxes/i);
  });

  it('reports a folder that cannot be listed', async () => {
    vi.mocked(annotate.listFolderImages).mockRejectedValue(new Error('nope'));
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.images).toHaveLength(0);
  });

  it('does nothing without a config', () => {
    const { result } = renderHook(() => useGeneratorSession(null));
    expect(result.current.currentImage).toBeNull();
    expect(annotate.listFolderImages).not.toHaveBeenCalled();
  });

  it('will not walk past either end of the folder', async () => {
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.images).toHaveLength(2));

    act(() => result.current.previous());
    expect(result.current.index).toBe(0);

    act(() => result.current.next());
    act(() => result.current.next());
    expect(result.current.index).toBe(1);
    expect(result.current.canGoNext).toBe(false);
  });

  it('keeps a hand-drawn box when the head has not been run', async () => {
    const { result } = renderHook(() => useGeneratorSession(CONFIG));
    await waitFor(() => expect(result.current.currentImage).not.toBeNull());

    act(() =>
      result.current.setBoxes([
        { id: 'x', label: 'positive', provenance: 'hand-drawn', x: 1, y: 1, w: 5, h: 5 },
      ]),
    );

    expect(result.current.boxes).toHaveLength(1);
  });
});

/**
 * Doc 70: what the session does with a review — returns it, saves it on leaving, refuses to
 * leave when that save fails, and shows it again on return.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExpertProposalResponse } from '../api/generate';
import { useGeneratorSession, type GeneratorConfig } from './useGeneratorSession';

vi.mock('../api/annotate', () => ({ listFolderImages: vi.fn() }));
vi.mock('../api/datasets', async (original) => ({
  ...(await original<Record<string, unknown>>()),
  saveImageBoxes: vi.fn(),
}));
vi.mock('../api/generate', async () => {
  const actual = await vi.importActual<typeof import('../api/generate')>('../api/generate');
  return { ...actual, proposeWithExpertHead: vi.fn() };
});

const annotate = await import('../api/annotate');
const datasets = await import('../api/datasets');
const generate = await import('../api/generate');

const CONFIG: GeneratorConfig = {
  kind: 'expert',
  datasetId: 'd1',
  images: { kind: 'folder', folder: '/photos' },
  backboneId: 'dinov2-small',
  instanceId: 'h1',
  scoreThreshold: 0.3,
};

const COUNTS = { images: 1, boxes: 1, masks: 0, positive: 1, negative: 0, unclear: 0 };

function proposalAt(x: number): ExpertProposalResponse {
  return {
    image_path: '/photos/a.png',
    width: 640,
    height: 480,
    device: 'cpu',
    head_name: 'Bolt finder',
    head_summary: 'Object detection',
    boxes: [
      {
        label: 'positive',
        provenance: 'expert-head',
        x,
        y: 20,
        w: 30,
        h: 40,
        prompt: 'bolt',
        score: 0.8,
        producer: { id: 'h1', label: 'Bolt finder' },
      },
    ],
  };
}

async function started() {
  const hook = renderHook(() => useGeneratorSession(CONFIG));
  await waitFor(() => expect(hook.result.current.currentImage).toBe('/photos/a.png'));
  return hook;
}

beforeEach(() => {
  vi.mocked(annotate.listFolderImages).mockResolvedValue(['/photos/a.png', '/photos/b.png']);
  vi.mocked(generate.proposeWithExpertHead).mockResolvedValue(proposalAt(10));
  vi.mocked(datasets.saveImageBoxes).mockResolvedValue(COUNTS as never);
});

afterEach(() => vi.clearAllMocks());

describe('useGeneratorSession — reviews (doc 70)', () => {
  it('returns what it proposed, tagged with the image it belongs to', async () => {
    const { result } = await started();
    let review: Awaited<ReturnType<typeof result.current.propose>> = null;
    await act(async () => {
      review = await result.current.propose();
    });
    expect(review).toMatchObject({ path: '/photos/a.png', imageSize: { width: 640 } });
    expect(review!.boxes[0]).toMatchObject({ x: 10, text: 'bolt' });
  });

  it('saves a dirty image before leaving it when auto-save is on', async () => {
    const { result } = await started();
    await act(async () => {
      await result.current.propose();
    });
    let moved = false;
    await act(async () => {
      moved = await result.current.next({ autoSave: true });
    });
    expect(moved).toBe(true);
    expect(datasets.saveImageBoxes).toHaveBeenCalledTimes(1);
    expect(vi.mocked(datasets.saveImageBoxes).mock.calls[0]![1]).toMatchObject({
      path: '/photos/a.png',
    });
    expect(result.current.currentImage).toBe('/photos/b.png');
  });

  it('does not save on leaving when auto-save is off', async () => {
    const { result } = await started();
    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.next({ autoSave: false });
    });
    expect(datasets.saveImageBoxes).not.toHaveBeenCalled();
    expect(result.current.currentImage).toBe('/photos/b.png');
  });

  it('stays on the image when the auto-save fails, so the review is not lost', async () => {
    vi.mocked(datasets.saveImageBoxes).mockRejectedValue(new Error('disk full'));
    const { result } = await started();
    await act(async () => {
      await result.current.propose();
    });
    let moved = true;
    await act(async () => {
      moved = await result.current.next({ autoSave: true });
    });
    expect(moved).toBe(false);
    expect(result.current.currentImage).toBe('/photos/a.png');
    expect(result.current.boxes).toHaveLength(1);
    expect(result.current.dirty).toBe(true);
    expect(result.current.error).toMatch(/disk full/);
  });

  it('shows the saved review again on return, clean rather than dirty', async () => {
    const { result } = await started();
    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.next({ autoSave: true });
    });
    expect(result.current.boxes).toHaveLength(0);

    await act(async () => {
      await result.current.previous();
    });
    expect(result.current.currentImage).toBe('/photos/a.png');
    expect(result.current.boxes[0]).toMatchObject({ x: 10 });
    expect(result.current.dirty).toBe(false);
    expect(result.current.saved('/photos/a.png')).toBeDefined();
    expect(result.current.saved('/photos/b.png')).toBeUndefined();
  });

  it('saves an explicit review rather than whatever state has rendered', async () => {
    // Autoplay's trap: propose and save in one breath, before React re-renders. A save
    // that read state would still see the empty list from before the proposal landed.
    const { result } = await started();
    await act(async () => {
      const review = await result.current.propose();
      await result.current.save(review!);
    });
    const saved = vi.mocked(datasets.saveImageBoxes).mock.calls[0]!;
    expect(saved[2]).toHaveLength(1);
    expect(saved[2][0]).toMatchObject({ x: 10 });
  });

  it('makes a hand edit saveable — drawing a box the model missed is a review too', async () => {
    // Found in the running app: only a proposal with results set `dirty`, so a box drawn
    // on an image where the model found nothing could never be saved.
    vi.mocked(generate.proposeWithExpertHead).mockResolvedValue({
      ...proposalAt(10),
      boxes: [],
    });
    const { result } = await started();
    await act(async () => {
      await result.current.propose();
    });
    expect(result.current.dirty).toBe(false);

    act(() =>
      result.current.setBoxes([
        { id: 'drawn', x: 1, y: 2, w: 3, h: 4, label: 'positive', text: 'pawn' } as never,
      ]),
    );
    expect(result.current.dirty).toBe(true);

    await act(async () => {
      await result.current.next({ autoSave: true });
    });
    expect(datasets.saveImageBoxes).toHaveBeenCalledTimes(1);
  });
});


/**
 * Head mode — the Annotation Studio running a head you trained instead of a phrase.
 *
 * The point of this file is that mode is chosen **once**, in the config, and nothing
 * downstream re-decides it: the same canvas, the same verdicts, the same save path. So the
 * tests assert on which endpoint was called and what reached the store, not on any flag.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { CONFIG, COUNTS, HEAD_CONFIG, box, json, route } from './session.testkit';
import { useAnnotationSession, type SessionConfig } from './useAnnotationSession';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

async function startedSession(config: SessionConfig, handlers = {}) {
  route(fetchMock, handlers);
  const { result } = renderHook(() => useAnnotationSession(config));
  await waitFor(() => expect(result.current.images).toHaveLength(3));
  act(() => result.current.reportImageSize(200, 100));
  return result;
}

function calledUrls(): string[] {
  return fetchMock.mock.calls.map(([input]) => String(input));
}

function putBody(): Record<string, unknown> {
  const put = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT');
  return JSON.parse(String(put?.[1]?.body));
}

describe('proposing from a trained head', () => {
  it('calls the expert endpoint and not the prompt detector', async () => {
    const result = await startedSession(HEAD_CONFIG);

    await act(async () => {
      await result.current.propose();
    });

    expect(calledUrls().some((url) => url.includes('/generate/expert'))).toBe(true);
    // The two modes are exclusive by decision — running both would double the review load.
    expect(calledUrls().some((url) => url.includes('/annotate') && !url.includes('folder'))).toBe(
      false,
    );
  });

  it('sends the head and backbone the config named', async () => {
    const result = await startedSession(HEAD_CONFIG);

    await act(async () => {
      await result.current.propose();
    });

    const call = fetchMock.mock.calls.find(([input]) => String(input).includes('/generate/expert'));
    expect(JSON.parse(String(call?.[1]?.body))).toMatchObject({
      image_path: '/pics/a.jpg',
      backbone_id: 'dinov2-small',
      instance_id: 'h1',
      score_threshold: 0.3,
    });
  });

  it('keeps the expert-head provenance rather than relabelling it', async () => {
    const result = await startedSession(HEAD_CONFIG);

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.boxes).toHaveLength(1);
    expect(result.current.boxes[0]?.provenance).toBe('expert-head');
  });

  it("carries each proposal's own class", async () => {
    // The class rides as `text` on the canvas and is renamed to `prompt` on save (doc 31).
    // Losing it here would make the saved dataset untrainable on its real classes.
    const result = await startedSession(HEAD_CONFIG);

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.boxes[0]?.text).toBe('person');
  });

  it('keeps hand-drawn boxes across a re-run, exactly as prompt mode does', async () => {
    const result = await startedSession(HEAD_CONFIG);

    act(() => result.current.setBoxes([box({ id: 'mine' })]));
    await act(async () => {
      await result.current.propose();
    });

    const provenances = result.current.boxes.map((b) => b.provenance);
    expect(provenances).toContain('hand-drawn');
    expect(provenances).toContain('expert-head');
  });

  it('reports a head failure in the head\'s own words', async () => {
    const result = await startedSession(HEAD_CONFIG, {
      expert: () => json({ error: { code: 'not_found', message: 'Unknown head' } }, 404),
    });

    await act(async () => {
      await result.current.propose();
    });

    expect(result.current.error).toBeTruthy();
    expect(result.current.error).not.toMatch(/detector/i);
  });
});

describe('saving what a head proposed', () => {
  it('sends no image-level prompt, because there was no phrase', async () => {
    // `replace_image_boxes` falls back to the image-level prompt when a box has none.
    // In head mode that fallback must not fire: each box carries its own class, and an
    // invented image-level prompt would overwrite nothing but would still be a fiction.
    const result = await startedSession(HEAD_CONFIG);

    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.save();
    });

    expect(putBody().prompt).toBeNull();
  });

  it('still sends the phrase in prompt mode', async () => {
    const result = await startedSession(CONFIG);

    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.save();
    });

    expect(putBody().prompt).toBe('a cat');
  });

  it('stores the counts the backend returned, like any other save', async () => {
    const result = await startedSession(HEAD_CONFIG);

    await act(async () => {
      await result.current.propose();
    });
    await act(async () => {
      await result.current.save();
    });

    expect(result.current.counts).toEqual(COUNTS);
    expect(result.current.dirty).toBe(false);
  });
});

/**
 * The concept a concept segmenter is actually run with (doc 45).
 *
 * This is a regression file, and it exists because of a bug the running app showed and no
 * test did. `run` was memoised on `[selected, backboneId, selectedFoundations]`, so it
 * closed over whatever `concept` was when the *selection* last changed — and since the
 * concept field only appears once a concept model is ticked, that was always `''`.
 *
 * Every Grounded SAM and SAM 3 run therefore went out with no concept, came back as an
 * all-background mask, and looked identical no matter what was typed. The assertions here
 * are on the **request body**, because that is where the bug was: the hook's own `concept`
 * was correct throughout, which is exactly why nothing caught it.
 */

import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { FOUNDATION, HEAD, IMAGE, fetchMock, json } from './headRun.testkit';
import { useHeadRun } from './useHeadRun';

const SEGMENTER = {
  ...FOUNDATION,
  id: 'grounded-sam',
  title: 'Grounded SAM (Grounding DINO + SAM 2.1)',
  task: 'segmentation',
  render_hint: 'masks',
  takes_concept: true,
};

function maskPrediction() {
  return {
    instance_id: 'grounded-sam',
    head_name: SEGMENTER.title,
    head_type_id: 'grounded-sam',
    task: 'segmentation',
    render_hint: 'masks',
    class_names: ['background', 'sky'],
    payload: { mask_png: 'x', present_classes: [0, 1], height: 4, width: 4 },
    grid: [0, 0],
    elapsed_ms: 900,
  };
}

/** Every `/foundation/predict` body sent, in order. */
const sent: Record<string, unknown>[] = [];

beforeEach(() => {
  sent.length = 0;
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockImplementation((input: unknown, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/foundation/predict')) {
      sent.push(JSON.parse(String(init?.body ?? '{}')) as Record<string, unknown>);
      return Promise.resolve(json(maskPrediction()));
    }
    if (url.includes('/foundation')) return Promise.resolve(json({ foundations: [SEGMENTER] }));
    if (url.includes('/heads')) return Promise.resolve(json({ heads: [HEAD] }));
    return Promise.resolve(json({}));
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

async function withSegmenterSelected() {
  const { result } = renderHook(() => useHeadRun(IMAGE));
  await waitFor(() => expect(result.current.foundations).toHaveLength(1));
  // The order a user is forced into: the concept field does not exist until the model
  // is ticked, so the concept is *always* typed after the selection changes.
  act(() => result.current.toggleFoundation('grounded-sam'));
  return result;
}

describe('the concept reaches the backend', () => {
  it('sends the concept typed after the model was selected', async () => {
    const result = await withSegmenterSelected();

    act(() => result.current.setConcept('sky'));
    await act(() => result.current.run(IMAGE));

    expect(sent).toHaveLength(1);
    expect(sent[0]?.['concept']).toBe('sky');
  });

  it('sends the new concept when it changes between runs', async () => {
    // "The mask stays the same, even when searching for something else."
    const result = await withSegmenterSelected();

    act(() => result.current.setConcept('sky'));
    await act(() => result.current.run(IMAGE));

    act(() => result.current.setConcept('rail track'));
    await act(() => result.current.run(IMAGE));

    expect(sent.map((body) => body['concept'])).toEqual(['sky', 'rail track']);
  });

  it('drops the previous result as soon as the concept changes', async () => {
    // A mask still on screen under a changed concept reads as though the new phrase
    // had been segmented.
    const result = await withSegmenterSelected();

    act(() => result.current.setConcept('sky'));
    await act(() => result.current.run(IMAGE));
    expect(result.current.result?.predictions).toHaveLength(1);

    act(() => result.current.setConcept('rail track'));
    expect(result.current.result).toBeNull();
  });
});

/** 2026-10-02: the viewer asks for every candidate and filters by its own threshold. */
import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { fetchMock, route } from './headRun.testkit';
import { useHeadRun } from './useHeadRun';

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe('a run of trained heads', () => {
  it('asks for every candidate, so the viewer can say what a weak head almost found', async () => {
    route();
    const { result } = renderHook(() => useHeadRun('/pics/a.jpg'));
    await waitFor(() => expect(result.current.heads).toHaveLength(1));
    act(() => result.current.toggle('h1'));
    await act(async () => {
      await result.current.run('/pics/a.jpg');
    });
    const compose = fetchMock.mock.calls.find(([url]) => String(url).includes('/inference/compose'));
    expect(JSON.parse(String(compose?.[1]?.body))).toMatchObject({ instance_ids: ['h1'], score_threshold: 0 });
  });
});

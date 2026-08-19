import { act, renderHook, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { DownloadJob, ModelInfo, SystemInfo } from '../api/models';
import { useModels } from './useModels';

const MODEL: ModelInfo = {
  id: 'dinov2-base',
  repo_id: 'facebook/dinov2-base',
  kind: 'backbone',
  family: 'dinov2',
  gated: false,
  approx_size_mb: 330,
  description: 'Balanced backbone.',
  licence: 'Apache-2.0',
  licence_url: 'https://huggingface.co/facebook/dinov2-base',
  requires_access_request: false,
  installed: false,
  size_on_disk_mb: 0,
  available: true,
  unavailable_reason: null,
};

const SYSTEM: SystemInfo = {
  device: 'mps',
  cache_dir: '/tmp/models',
  hf_token_present: false,
  free_disk_mb: 100_000,
};

function job(state: DownloadJob['state'], extra: Partial<DownloadJob> = {}): DownloadJob {
  return {
    job_id: 'job-1',
    model_id: 'dinov2-base',
    state,
    downloaded_bytes: 0,
    total_bytes: 0,
    message: '',
    ...extra,
  };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const fetchMock = vi.fn<typeof fetch>();

/** Route by URL + method so the hook's real call sequence is exercised. */
function route(handlers: {
  models?: () => Response;
  system?: () => Response;
  download?: () => Response;
  jobs?: () => Response;
  del?: () => Response;
}): void {
  fetchMock.mockImplementation((input, init) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    if (url.includes('/system/info')) return Promise.resolve((handlers.system ?? (() => json(SYSTEM)))());
    if (url.includes('/models/jobs/')) return Promise.resolve((handlers.jobs ?? (() => json(job('complete'))))());
    if (url.includes('/download')) return Promise.resolve((handlers.download ?? (() => json(job('pending'))))());
    if (method === 'DELETE') return Promise.resolve((handlers.del ?? (() => json({ id: MODEL.id, removed: true, freed_mb: 330 })))());
    return Promise.resolve((handlers.models ?? (() => json({ models: [MODEL] })))());
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useModels', () => {
  it('loads the catalogue and system info on mount', async () => {
    route({});
    const { result } = renderHook(() => useModels());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.models).toHaveLength(1);
    expect(result.current.models[0]?.id).toBe('dinov2-base');
    expect(result.current.system?.device).toBe('mps');
    expect(result.current.error).toBeNull();
  });

  it('surfaces a backend error instead of rendering an empty catalogue', async () => {
    route({ models: () => json({ error: { code: 'internal_error', message: 'boom' } }, 500) });
    const { result } = renderHook(() => useModels());

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe('boom');
    expect(result.current.models).toHaveLength(0);
  });

  it('polls a download to completion and refreshes the catalogue', async () => {
    const states: DownloadJob['state'][] = ['downloading', 'complete'];
    let call = 0;
    route({
      jobs: () => json(job(states[Math.min(call++, states.length - 1)] ?? 'complete')),
      models: () => json({ models: [{ ...MODEL, installed: true, size_on_disk_mb: 331 }] }),
    });

    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.download('dinov2-base');
    });

    expect(result.current.jobs['dinov2-base']?.state).toBe('complete');
    await waitFor(() => expect(result.current.models[0]?.installed).toBe(true));
  });

  it('reports a failed download through the error channel', async () => {
    route({ jobs: () => json(job('failed', { message: 'RuntimeError while downloading' })) });

    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.download('dinov2-base');
    });

    expect(result.current.jobs['dinov2-base']?.state).toBe('failed');
    expect(result.current.error).toContain('RuntimeError');
  });

  it('surfaces a 403 on a gated model without starting a job', async () => {
    route({
      download: () =>
        json({ error: { code: 'forbidden', message: 'dinov3-vitb16 is gated.' } }, 403),
    });

    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.download('dinov3-vitb16');
    });

    expect(result.current.error).toContain('gated');
    expect(result.current.jobs['dinov3-vitb16']).toBeUndefined();
  });

  it('removes a model and refreshes', async () => {
    route({});
    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.remove('dinov2-base');
    });

    const deleteCall = fetchMock.mock.calls.find(([, init]) => init?.method === 'DELETE');
    expect(deleteCall?.[0]).toContain('/models/dinov2-base');
    expect(result.current.error).toBeNull();
  });

  it('clears the busy flag after a failed action', async () => {
    route({ download: () => json({ error: { code: 'conflict', message: 'nope' } }, 409) });

    const { result } = renderHook(() => useModels());
    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.download('dinov2-base');
    });

    expect(result.current.busy['dinov2-base']).toBe(false);
  });
});

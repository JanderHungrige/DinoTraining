/** Jan's second machine: the backend needed ~4 s beside the app, and nothing asked again. */

import { afterEach, describe, expect, it, vi } from 'vitest';

const ok = (): Response => new Response(JSON.stringify({ datasets: [] }), { status: 200 });
const isList = (v: unknown): v is { datasets: unknown[] } => typeof v === 'object' && v !== null && 'datasets' in v;

async function freshClient() {
  vi.resetModules();
  const wait = await import('./startupWait');
  wait.setStartupWait(30_000);
  const client = await import('./client');
  return { wait, client };
}

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('reads wait for a backend that is still starting', () => {
  it('retries a failed read until the backend answers', async () => {
    vi.useFakeTimers();
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('Could not connect to the server.'))
      .mockRejectedValueOnce(new TypeError('Could not connect to the server.'))
      .mockResolvedValue(ok());
    vi.stubGlobal('fetch', fetchMock);
    const { client } = await freshClient();
    const listed = client.apiFetch('/datasets', isList);
    await vi.advanceTimersByTimeAsync(1_000);
    await expect(listed).resolves.toEqual({ datasets: [] });
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it('never retries a write: it could run twice', async () => {
    const fetchMock = vi.fn().mockRejectedValue(new TypeError('Could not connect to the server.'));
    vi.stubGlobal('fetch', fetchMock);
    const { client } = await freshClient();
    await expect(client.apiFetch('/datasets', isList, { method: 'POST' })).rejects.toMatchObject({ code: 'unreachable' });
    expect(fetchMock).toHaveBeenCalledOnce();
  });

  it('once the backend has answered, a lost connection is reported at once', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(ok()).mockRejectedValue(new TypeError('Could not connect to the server.'));
    vi.stubGlobal('fetch', fetchMock);
    const { client } = await freshClient();
    await client.apiFetch('/datasets', isList);
    await expect(client.apiFetch('/datasets', isList)).rejects.toMatchObject({ code: 'unreachable' });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

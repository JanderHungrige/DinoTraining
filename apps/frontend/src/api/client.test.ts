import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { API_BASE_URL, API_PREFIX, ApiError, apiFetch, getHealth } from './client';
import { isHealthResponse, type HealthResponse } from './types';

const VALID_HEALTH: HealthResponse = {
  status: 'ok',
  version: '0.0.1',
  device: 'mps',
  api_prefix: '/api/v1',
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('apiFetch', () => {
  it('requests the versioned URL built from base + prefix + path', async () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_HEALTH));

    await apiFetch('/health', isHealthResponse);

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe(`${API_BASE_URL}${API_PREFIX}/health`);
  });

  it('normalises a path given without a leading slash', async () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_HEALTH));

    await apiFetch('health', isHealthResponse);

    const [url] = fetchMock.mock.calls[0] ?? [];
    expect(url).toBe(`${API_BASE_URL}${API_PREFIX}/health`);
  });

  it('returns the decoded body when the shape matches', async () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_HEALTH));

    await expect(apiFetch('/health', isHealthResponse)).resolves.toEqual(VALID_HEALTH);
  });

  it('throws an unreachable ApiError when the transport fails', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'));

    const error = await apiFetch('/health', isHealthResponse).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(0);
    expect((error as ApiError).code).toBe('unreachable');
    expect((error as ApiError).isUnreachable).toBe(true);
  });

  it('surfaces the backend error envelope on a non-2xx response', async () => {
    fetchMock.mockResolvedValue(
      jsonResponse({ error: { code: 'not_found', message: 'no such thing' } }, 404),
    );

    const error = await apiFetch('/nope', isHealthResponse).catch((e: unknown) => e);

    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(404);
    expect((error as ApiError).code).toBe('not_found');
    expect((error as ApiError).message).toBe('no such thing');
  });

  it('falls back to a generic error when a failure body is not our envelope', async () => {
    fetchMock.mockResolvedValue(new Response('<html>gateway blew up</html>', { status: 502 }));

    const error = (await apiFetch('/health', isHealthResponse).catch(
      (e: unknown) => e,
    )) as ApiError;

    expect(error.status).toBe(502);
    expect(error.code).toBe('http_error');
  });

  it('rejects a 200 whose body does not match the expected shape', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ status: 'ok', version: 1, device: 'quantum' }));

    const error = (await apiFetch('/health', isHealthResponse).catch(
      (e: unknown) => e,
    )) as ApiError;

    expect(error.code).toBe('malformed_response');
    expect(error.message).toContain('drifted');
  });

  it('always asks for JSON', async () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_HEALTH));

    await apiFetch('/health', isHealthResponse);

    const init = fetchMock.mock.calls[0]?.[1];
    expect(init?.headers).toMatchObject({ Accept: 'application/json' });
  });
});

describe('getHealth', () => {
  it('calls /health and returns the parsed payload', async () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_HEALTH));

    await expect(getHealth()).resolves.toEqual(VALID_HEALTH);
    expect(fetchMock.mock.calls[0]?.[0]).toBe(`${API_BASE_URL}${API_PREFIX}/health`);
  });

  it('passes an abort signal through to fetch', async () => {
    fetchMock.mockResolvedValue(jsonResponse(VALID_HEALTH));
    const controller = new AbortController();

    await getHealth(controller.signal);

    expect(fetchMock.mock.calls[0]?.[1]?.signal).toBe(controller.signal);
  });

  it('rejects a device the backend should never send', async () => {
    fetchMock.mockResolvedValue(jsonResponse({ ...VALID_HEALTH, device: 'auto' }));

    const error = (await getHealth().catch((e: unknown) => e)) as ApiError;

    expect(error.code).toBe('malformed_response');
  });
});

/**
 * The single door to the backend.
 *
 * Nothing in the UI calls `fetch()` directly — everything goes through `apiFetch`,
 * which owns the base URL, JSON handling, and error shaping. One place to add auth,
 * retries, or telemetry later; one place to look when a call misbehaves.
 */

import {
  isApiErrorBody,
  isHealthResponse,
  type ApiErrorBody,
  type HealthResponse,
} from './types';

const DEFAULT_BASE_URL = 'http://127.0.0.1:8756';

/** Overridable for the Wave 6 website build, where the backend is not on loopback. */
export const API_BASE_URL: string = import.meta.env['VITE_DINO_API_URL'] ?? DEFAULT_BASE_URL;

export const API_PREFIX = '/api/v1';

/** A structured failure from the backend, or from the transport in front of it. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.details = details;
  }

  /** True when the sidecar is not accepting connections yet (or at all). */
  get isUnreachable(): boolean {
    return this.status === 0;
  }
}

function buildUrl(path: string): string {
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${API_PREFIX}${suffix}`;
}

/**
 * Absolute URL for an API path.
 *
 * Exported for `EventSource`, which takes a URL rather than going through `apiFetch`.
 * Sharing `buildUrl` keeps SSE on the same base and prefix as every other call — a
 * second URL builder is how a stream ends up pointing at the wrong port in packaged
 * builds while fetches keep working.
 */
export function apiUrl(path: string): string {
  return buildUrl(path);
}

async function readErrorBody(response: Response): Promise<ApiErrorBody['error']> {
  try {
    const body: unknown = await response.json();
    if (isApiErrorBody(body)) return body.error;
  } catch {
    // Body was empty or not JSON — fall through to the generic shape below.
  }
  return { code: 'http_error', message: `${response.status} ${response.statusText}`.trim() };
}

/**
 * Call a `/api/v1/*` endpoint and return its decoded body.
 *
 * @param path   Path *after* the version prefix, e.g. `/health`.
 * @param narrow Runtime guard for the response. Required: a wrong shape must fail
 *               here, at the boundary, rather than leak `undefined` into the UI.
 * @throws {ApiError} on transport failure, non-2xx status, or a shape mismatch.
 */
export async function apiFetch<T>(
  path: string,
  narrow: (value: unknown) => value is T,
  init?: RequestInit,
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path), {
      ...init,
      headers: { Accept: 'application/json', ...init?.headers },
    });
  } catch (cause) {
    throw new ApiError(
      0,
      'unreachable',
      `Cannot reach the DinoTraining backend at ${API_BASE_URL}. Is the sidecar running?`,
      cause,
    );
  }

  if (!response.ok) {
    const error = await readErrorBody(response);
    throw new ApiError(response.status, error.code, error.message, error.details);
  }

  const body: unknown = await response.json();
  if (!narrow(body)) {
    throw new ApiError(
      response.status,
      'malformed_response',
      `Unexpected response shape from ${path}. Backend and frontend contracts have drifted.`,
      body,
    );
  }
  return body;
}

/** `GET /api/v1/health` — the sidecar readiness probe. */
export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiFetch('/health', isHealthResponse, signal ? { signal } : undefined);
}

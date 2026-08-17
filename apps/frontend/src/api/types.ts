/**
 * Shapes returned by the FastAPI sidecar.
 *
 * These mirror the Pydantic models in `backend/app/api/v1/`. When you change one
 * side, change the other in the same commit — that pairing is the whole contract.
 */

/** Resolved compute device. Never `auto` — the backend resolves that before responding. */
export type Device = 'cuda' | 'mps' | 'cpu';

/** `GET /api/v1/health` — mirrors `HealthResponse` in backend/app/api/v1/health.py */
export interface HealthResponse {
  readonly status: 'ok';
  readonly version: string;
  readonly device: Device;
  readonly api_prefix: string;
}

/** Canonical error envelope — mirrors `error_body()` in backend/app/core/errors.py */
export interface ApiErrorBody {
  readonly error: {
    readonly code: string;
    readonly message: string;
    readonly details?: unknown;
  };
}

export const DEVICES: readonly Device[] = Object.freeze(['cuda', 'mps', 'cpu'] as const);

export function isDevice(value: unknown): value is Device {
  return typeof value === 'string' && (DEVICES as readonly string[]).includes(value);
}

/**
 * Runtime narrowing for the health payload.
 *
 * `response.json()` returns `any`-shaped data from outside the type system, so it
 * gets checked rather than asserted — a backend/frontend drift should surface as a
 * clear error here, not as `undefined` three components away.
 */
export function isHealthResponse(value: unknown): value is HealthResponse {
  if (typeof value !== 'object' || value === null) return false;
  const candidate = value as Record<string, unknown>;
  return (
    candidate['status'] === 'ok' &&
    typeof candidate['version'] === 'string' &&
    typeof candidate['api_prefix'] === 'string' &&
    isDevice(candidate['device'])
  );
}

export function isApiErrorBody(value: unknown): value is ApiErrorBody {
  if (typeof value !== 'object' || value === null) return false;
  const error = (value as Record<string, unknown>)['error'];
  if (typeof error !== 'object' || error === null) return false;
  const candidate = error as Record<string, unknown>;
  return typeof candidate['code'] === 'string' && typeof candidate['message'] === 'string';
}

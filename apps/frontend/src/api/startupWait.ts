/**
 * Reads wait for the backend while the app starts.
 *
 * The desktop shell starts the backend and the UI together, and the UI asks for its lists
 * at once. On a slower machine the backend needs a few seconds, every first request failed
 * with "could not connect", and nothing asked again: no datasets, no models, although the
 * backend reported healthy moments later (Jan, 2026-09-30, a second machine).
 *
 * So until the backend has answered once, a failed read is retried for a short startup
 * window. After that first answer a connection failure is reported at once — a backend
 * that died later must not look like a slow one.
 */

const STARTED_AT = Date.now();
export const RETRY_EVERY_MS = 500;
let windowMs = 30_000;
let reached = false;

/** Tests set 0, so an unreachable backend fails at once. */
export function setStartupWait(ms: number): void {
  windowMs = ms;
}

export function markBackendReached(): void {
  reached = true;
}

/** Whether a failed read may be tried again: only before the backend first answered. */
export function mayRetry(method: string | undefined, signal: AbortSignal | null | undefined): boolean {
  const read = method === undefined || method.toUpperCase() === 'GET';
  return read && !reached && !signal?.aborted && Date.now() - STARTED_AT < windowMs;
}

export function pause(ms: number, signal: AbortSignal | null | undefined): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener('abort', () => {
      clearTimeout(timer);
      resolve();
    });
  });
}

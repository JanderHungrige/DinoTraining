/**
 * Live sidecar status badge.
 *
 * The Tauri shell already gates startup on `/api/v1/health`, but the sidecar can die
 * later (OOM during training is the realistic case). This keeps polling so the user
 * finds out from the UI rather than from a request that hangs.
 */

import { useEffect, useState, type JSX } from 'react';

import { ApiError, getHealth } from '../api/client';
import type { HealthResponse } from '../api/types';

const POLL_INTERVAL_MS = 5_000;

type Status =
  | { readonly kind: 'connecting' }
  | { readonly kind: 'ready'; readonly health: HealthResponse }
  | { readonly kind: 'unreachable'; readonly message: string };

export function BackendStatus(): JSX.Element {
  const [status, setStatus] = useState<Status>({ kind: 'connecting' });

  useEffect(() => {
    const controller = new AbortController();
    let cancelled = false;

    const poll = async (): Promise<void> => {
      try {
        const health = await getHealth(controller.signal);
        if (!cancelled) setStatus({ kind: 'ready', health });
      } catch (error) {
        if (cancelled || controller.signal.aborted) return;
        const message =
          error instanceof ApiError ? error.message : 'Unexpected error contacting the backend.';
        setStatus({ kind: 'unreachable', message });
      }
    };

    void poll();
    const timer = window.setInterval(() => void poll(), POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      controller.abort();
      window.clearInterval(timer);
    };
  }, []);

  if (status.kind === 'ready') {
    const { version, device } = status.health;
    return (
      <p className="status status--ready" role="status">
        <span className="status__dot" aria-hidden="true" />
        Backend v{version} · {device.toUpperCase()}
      </p>
    );
  }

  if (status.kind === 'connecting') {
    return (
      <p className="status status--pending" role="status">
        <span className="status__dot" aria-hidden="true" />
        Connecting to backend…
      </p>
    );
  }

  return (
    <p className="status status--error" role="alert">
      <span className="status__dot" aria-hidden="true" />
      {status.message}
    </p>
  );
}

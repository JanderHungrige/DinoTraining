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
import { useT } from '../i18n';

const POLL_INTERVAL_MS = 5_000;

type Status =
  | { readonly kind: 'connecting' }
  | { readonly kind: 'ready'; readonly health: HealthResponse }
  | { readonly kind: 'unreachable'; readonly message: string | null };

export function BackendStatus(): JSX.Element {
  const { t } = useT();
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
        // Only an ApiError carries a message worth showing; anything else is shown as
        // `null` and worded at render, so a language switch rewords it too.
        setStatus({ kind: 'unreachable', message: error instanceof ApiError ? error.message : null });
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
        {t('app.backend.connecting')}
      </p>
    );
  }

  return (
    <p className="status status--error" role="alert">
      <span className="status__dot" aria-hidden="true" />
      {status.message ?? t('app.backend.unexpected')}
    </p>
  );
}

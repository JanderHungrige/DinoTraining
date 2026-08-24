/**
 * State for the head catalogue section of the Admin tab.
 *
 * Installs are awaited rather than polled: a head is single-digit MB, so the request
 * completes in about the time a spinner is up. The model downloader polls because
 * backbones are hundreds of MB — same tab, different scale, deliberately different
 * mechanism.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

import { ApiError } from '../api/client';
import {
  importCommunityHead,
  installCatalogEntry,
  listHeadCatalog,
  type CatalogEntry,
  type ImportRequest,
} from '../api/headCatalog';

export interface UseHeadCatalogResult {
  readonly entries: readonly CatalogEntry[];
  readonly loading: boolean;
  readonly error: string | null;
  readonly notice: string | null;
  readonly busy: Readonly<Record<string, boolean>>;
  readonly install: (entryId: string) => Promise<void>;
  readonly importHead: (request: ImportRequest) => Promise<boolean>;
  readonly refresh: () => Promise<void>;
}

function describeError(error: unknown, fallback: string): string {
  return error instanceof ApiError ? error.message : fallback;
}

export function useHeadCatalog(backbone?: string): UseHeadCatalogResult {
  const [entries, setEntries] = useState<readonly CatalogEntry[]>([]);
  const [busy, setBusy] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const refresh = useCallback(async (): Promise<void> => {
    try {
      const next = await listHeadCatalog(backbone);
      if (!mounted.current) return;
      setEntries(next);
      setError(null);
    } catch (cause) {
      if (mounted.current) setError(describeError(cause, 'Could not load the head catalogue.'));
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [backbone]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const install = useCallback(
    async (entryId: string): Promise<void> => {
      setBusy((current) => ({ ...current, [entryId]: true }));
      try {
        const instance = await installCatalogEntry(entryId);
        if (!mounted.current) return;
        // The backend's summary, not one composed here — doc 12's cross-tab contract.
        setNotice(`Installed: ${instance.summary}`);
        setError(null);
        await refresh();
      } catch (cause) {
        if (mounted.current) setError(describeError(cause, 'Could not install the head.'));
      } finally {
        if (mounted.current) setBusy((current) => ({ ...current, [entryId]: false }));
      }
    },
    [refresh],
  );

  const importHead = useCallback(
    async (request: ImportRequest): Promise<boolean> => {
      setBusy((current) => ({ ...current, import: true }));
      try {
        const instance = await importCommunityHead(request);
        if (!mounted.current) return true;
        setNotice(`Imported: ${instance.summary}`);
        setError(null);
        await refresh();
        return true;
      } catch (cause) {
        // Returned rather than thrown so the form can stay open with its values
        // intact — a rejected import is usually a one-character fix in the repo id.
        if (mounted.current) setError(describeError(cause, 'Could not import that head.'));
        return false;
      } finally {
        if (mounted.current) setBusy((current) => ({ ...current, import: false }));
      }
    },
    [refresh],
  );

  return { entries, loading, error, notice, busy, install, importHead, refresh };
}

/**
 * Wave 4 — the user's own HuggingFace token and licence acknowledgements.
 * Mirrors backend/app/api/v1/settings.py.
 *
 * The token travels one way. Nothing here has a type that could hold it coming back:
 * `TokenStatus` carries a boolean and a masked hint, and that is the whole contract.
 */

import { apiFetch } from './client';

export interface TokenStatus {
  readonly configured: boolean;
  /** At most the last four characters — enough to tell which token is stored. */
  readonly hint: string | null;
  /** Absolute path, so the user can edit the file by hand if they prefer. */
  readonly env_file: string;
  readonly accepted_licences: readonly string[];
}

export interface LicenceNotice {
  readonly model_id: string;
  readonly licence: string;
  readonly licence_url: string;
  readonly requires_access_request: boolean;
  readonly accepted: boolean;
  /** Written by the backend beside the flag that makes it true, so the two cannot drift. */
  readonly explanation: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

function isTokenStatus(value: unknown): value is TokenStatus {
  if (!isRecord(value)) return false;
  return (
    typeof value['configured'] === 'boolean' &&
    typeof value['env_file'] === 'string' &&
    Array.isArray(value['accepted_licences'])
  );
}

function isLicenceNoticeList(
  value: unknown,
): value is { notices: readonly LicenceNotice[] } {
  return (
    isRecord(value) &&
    Array.isArray(value['notices']) &&
    value['notices'].every(
      (entry) =>
        isRecord(entry) &&
        typeof entry['model_id'] === 'string' &&
        typeof entry['explanation'] === 'string',
    )
  );
}

export async function fetchTokenStatus(signal?: AbortSignal): Promise<TokenStatus> {
  return apiFetch('/settings/hf-token', isTokenStatus, signal ? { signal } : undefined);
}

export async function saveToken(token: string): Promise<TokenStatus> {
  return apiFetch('/settings/hf-token', isTokenStatus, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
}

export async function clearToken(): Promise<TokenStatus> {
  return apiFetch('/settings/hf-token', isTokenStatus, { method: 'DELETE' });
}

export async function fetchLicenceNotices(
  signal?: AbortSignal,
): Promise<readonly LicenceNotice[]> {
  const body = await apiFetch(
    '/settings/licences',
    isLicenceNoticeList,
    signal ? { signal } : undefined,
  );
  return body.notices;
}

export async function acceptLicence(modelId: string): Promise<TokenStatus> {
  return apiFetch('/settings/accepted-licences', isTokenStatus, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_id: modelId }),
  });
}

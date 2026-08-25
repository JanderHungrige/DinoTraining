/**
 * The API guide, fetched from the backend that serves it (doc 63).
 *
 * Not bundled into the frontend: the guide's endpoint reference is generated from the
 * running backend's own OpenAPI schema, so a copy shipped in the UI would describe whatever
 * the API looked like when the app was built. Fetching it means the document always
 * describes the process answering the calls.
 */

import { API_BASE_URL, API_PREFIX } from './client';

export const GUIDE_FILENAME = 'dinotraining-api-guide.md';

/** The guide as markdown. Plain `fetch` because `apiFetch` is a JSON door. */
export async function fetchAgentGuide(signal?: AbortSignal): Promise<string> {
  const response = await fetch(`${API_BASE_URL}${API_PREFIX}/docs/agent-guide`, {
    ...(signal ? { signal } : {}),
  });
  if (!response.ok) {
    throw new Error(`Could not load the API guide (${response.status}).`);
  }
  return response.text();
}

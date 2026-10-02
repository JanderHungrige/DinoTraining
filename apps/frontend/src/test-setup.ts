import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

import { setStartupWait } from './api/startupWait';

// The startup wait (a slow backend beside the desktop app) would make every
// "unreachable" test wait 30 s.
setStartupWait(0);

afterEach(() => {
  cleanup();
  // Doc 69: forms remember their entries. Without this, one test's typed folder would
  // silently pre-fill the next test's form.
  localStorage.clear();
});

// Tests never reach the network. A component a test does not mock (the backend badge, a
// settings catalogue) would otherwise call a backend on :8756 for real, and the test then
// passes or fails depending on whether one happens to be running: the recipe test passed
// for weeks against a forgotten dev backend (2026-10-02). Every real request fails at
// once, as an unreachable backend does; a test that needs an answer mocks its API module
// or stubs fetch itself.
globalThis.fetch = (input: RequestInfo | URL) => {
  const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
  return Promise.reject(new TypeError(`Tests never reach the network (${url})`));
};

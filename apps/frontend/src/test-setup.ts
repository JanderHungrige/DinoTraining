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

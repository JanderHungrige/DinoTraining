import '@testing-library/jest-dom/vitest';

import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

afterEach(() => {
  cleanup();
  // Doc 69: forms remember their entries. Without this, one test's typed folder would
  // silently pre-fill the next test's form.
  localStorage.clear();
});

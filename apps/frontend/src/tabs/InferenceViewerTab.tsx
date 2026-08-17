import type { JSX } from 'react';

import { StubPanel } from '../components/StubPanel';

/** Wave 3 — inference viewer UI. */
export function InferenceViewerTab(): JSX.Element {
  return <StubPanel tabId="inference" />;
}

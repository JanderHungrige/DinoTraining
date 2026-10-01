/** Rendering in German, for tests (doc 112). */

import { render, type RenderResult } from '@testing-library/react';
import type { ReactElement } from 'react';

import { storageKeyFor } from '../lib/persisted';
import { LanguageProvider } from './LanguageProvider';

export function renderInGerman(ui: ReactElement): RenderResult {
  localStorage.setItem(storageKeyFor('language'), JSON.stringify('de'));
  return render(<LanguageProvider>{ui}</LanguageProvider>);
}

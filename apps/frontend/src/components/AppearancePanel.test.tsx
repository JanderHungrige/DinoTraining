import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { LookProvider } from '../lib/look';
import { AppearancePanel } from './AppearancePanel';

afterEach(() => vi.unstubAllGlobals());

function withMotion(reduce: boolean): void {
  vi.stubGlobal('matchMedia', () => ({
    matches: reduce,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

describe('AppearancePanel (doc 77)', () => {
  it('is on by default', () => {
    withMotion(false);
    render(
      <LookProvider>
        <AppearancePanel />
      </LookProvider>,
    );
    expect(screen.getByRole('checkbox', { name: /animated background/i })).toBeChecked();
    expect(screen.queryByText(/reduced motion/)).not.toBeInTheDocument();
  });

  it('says why the background is still when the system asks for reduced motion', () => {
    withMotion(true);
    render(
      <LookProvider>
        <AppearancePanel />
      </LookProvider>,
    );
    expect(screen.getByText(/asks for reduced motion/)).toBeInTheDocument();
  });
});

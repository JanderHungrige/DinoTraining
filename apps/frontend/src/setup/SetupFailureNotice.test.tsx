import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { renderInGerman } from '../i18n/testing';
import { percent } from './shell';
import { SetupFailureNotice } from './SetupFailureNotice';

vi.mock('../components/ErrorActions', () => ({ ErrorActions: () => null }));

describe('the Visual C++ runtime failure (doc 141)', () => {
  it("says what PyTorch needs, what this PC has, why, and where to get it", () => {
    render(<SetupFailureNotice failure={{ kind: 'vc_runtime', found: '14.28.29334', reason: 'declined', code: null }} onRetry={() => undefined} />);
    const text = screen.getByRole('alert').textContent ?? '';
    expect(text).toContain('Microsoft Visual C++ runtime 14.40 or newer, and this PC has 14.28.29334.');
    expect(text).toContain("Windows' permission to install it was declined.");
    expect(text).toContain('https://aka.ms/vs/17/release/vc_redist.x64.exe');
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('names a missing runtime and the installer error code, in German', () => {
    renderInGerman(<SetupFailureNotice failure={{ kind: 'vc_runtime', found: null, reason: 'installer', code: 1603 }} onRetry={() => undefined} />);
    const text = screen.getByRole('alert').textContent ?? '';
    expect(text).toContain('dieser PC hat keine.');
    expect(text).toContain('mit Fehler 1603 abgebrochen');
  });

  it('the runtime phase leaves the bar at the start', () => {
    expect(percent({ phase: 'runtime', done_mb: 0, total_mb: 0, current: null })).toBe(0);
  });
});

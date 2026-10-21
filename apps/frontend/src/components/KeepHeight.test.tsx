import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { KeepHeight } from './KeepHeight';

afterEach(() => vi.restoreAllMocks());

describe('KeepHeight (2026-10-21)', () => {
  it('keeps the last height while a placeholder shows, so the page does not shrink', () => {
    vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockReturnValue(640);
    const { rerender } = render(<KeepHeight holding={false}><div>canvas and list</div></KeepHeight>);
    const box = screen.getByText('canvas and list').parentElement as HTMLElement;
    expect(box.style.minHeight).toBe('');

    rerender(<KeepHeight holding><p>Loading the image…</p></KeepHeight>);
    expect(box.style.minHeight).toBe('640px');

    rerender(<KeepHeight holding={false}><div>the next picture</div></KeepHeight>);
    expect(box.style.minHeight).toBe('');
  });
});

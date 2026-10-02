/** The Studio survives a visit to another tab: App keeps it mounted (Jan, 2026-09-30). */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState, type JSX } from 'react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('./tabs/AnnotationStudioTab', () => ({
  AnnotationStudioTab: ({ active = true }: { readonly active?: boolean }): JSX.Element => {
    const [count, setCount] = useState(0);
    return (
      <button type="button" data-active={String(active)} onClick={() => setCount((n) => n + 1)}>
        studio state {count}
      </button>
    );
  },
}));
vi.mock('./components/BackendStatus', () => ({ BackendStatus: () => null }));
vi.mock('./components/BackgroundVideo', () => ({ BackgroundVideo: () => null }));
vi.mock('./tabs/ModelsTab', () => ({ ModelsTab: () => <p>models</p> }));

import { App } from './App';

describe('App keeps the Studio session', () => {
  it('keeps the Studio mounted, hidden and inactive, while another tab is shown', async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(screen.getByRole('tab', { name: 'Annotation Studio' }));
    await user.click(screen.getByRole('button', { name: 'studio state 0' }));
    await user.click(screen.getByRole('tab', { name: 'Models & Datasets' }));
    const hidden = screen.getByText('studio state 1', { selector: 'button' });
    expect(hidden.closest('[hidden]')).not.toBeNull();
    expect(hidden).toHaveAttribute('data-active', 'false');
    await user.click(screen.getByRole('tab', { name: 'Annotation Studio' }));
    const shown = screen.getByRole('button', { name: 'studio state 1' });
    expect(shown.closest('[hidden]')).toBeNull();
    expect(shown).toHaveAttribute('data-active', 'true');
  });
});

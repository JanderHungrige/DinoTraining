import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderInGerman } from '../i18n/testing';
import { BackgroundVideo } from '../components/BackgroundVideo';
import { LookProvider } from '../lib/look';
import { BACKGROUND_SOURCE, SettingsTab } from './SettingsTab';

let systemLight = false;
const listeners = new Set<() => void>();

beforeEach(() => {
  systemLight = false;
  vi.stubGlobal('matchMedia', (query: string) => ({
    get matches() {
      return query.includes('light') && systemLight;
    },
    addEventListener: (_: string, cb: () => void) => listeners.add(cb),
    removeEventListener: (_: string, cb: () => void) => listeners.delete(cb),
  }));
});

afterEach(() => {
  vi.unstubAllGlobals();
  listeners.clear();
  delete document.documentElement.dataset['theme'];
  delete document.documentElement.dataset['background'];
});

const theme = (): string | undefined => document.documentElement.dataset['theme'];

function renderSettings(): void {
  render(
    <LookProvider>
      <SettingsTab />
    </LookProvider>,
  );
}

describe('Settings (doc 164)', () => {
  it('follows the system by default, also when the system changes', () => {
    renderSettings();
    expect(screen.getByRole('radio', { name: 'Like the system' })).toBeChecked();
    expect(theme()).toBe('dark');
    systemLight = true;
    act(() => listeners.forEach((cb) => cb()));
    expect(theme()).toBe('light');
  });

  it('applies a chosen scheme at once, and remembers it', async () => {
    const user = userEvent.setup();
    renderSettings();
    await user.click(screen.getByRole('radio', { name: 'Light' }));
    expect(theme()).toBe('light');
    expect(localStorage.getItem('dinotraining.v1.look.theme')).toBe('"light"');
    await user.click(screen.getByRole('radio', { name: 'Dark' }));
    expect(theme()).toBe('dark');
    systemLight = true;
    act(() => listeners.forEach((cb) => cb()));
    expect(theme()).toBe('dark'); // a choice wins over the system
  });

  it('holds the animated-background switch and the background credit', () => {
    renderSettings();
    expect(screen.getByRole('checkbox', { name: 'Animated background' })).toBeChecked();
    expect(screen.getByRole('link', { name: 'Open on Pexels' })).toHaveAttribute('href', BACKGROUND_SOURCE);
    expect(BACKGROUND_SOURCE).toBe('https://www.pexels.com/video/trees-in-the-forest-5121476/');
  });

  it('speaks German', () => {
    renderInGerman(
      <LookProvider>
        <SettingsTab />
      </LookProvider>,
    );
    expect(screen.getByRole('heading', { name: 'Einstellungen' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Wie das System' })).toBeChecked();
    expect(screen.getByText(/„Trees in the forest“, ein Video von Pexels/)).toBeInTheDocument();
  });

  it('switches the background, its treatment and the video at once (doc 165)', async () => {
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(
      <LookProvider>
        <BackgroundVideo />
        <SettingsTab />
      </LookProvider>,
    );
    expect(screen.getByRole('radio', { name: 'Forest' })).toBeChecked();
    expect(document.documentElement.dataset['background']).toBe('forest');
    expect(document.querySelector('.bgvideo video')).toHaveAttribute('src', expect.stringContaining('particles-loop.mp4'));

    await user.click(screen.getByRole('radio', { name: 'Particles' }));
    expect(document.documentElement.dataset['background']).toBe('particles');
    expect(document.querySelector('.bgvideo video')).toHaveAttribute('src', expect.stringContaining('original-particles.mp4'));
    expect(localStorage.getItem('dinotraining.v1.look.background')).toBe('"particles"');
  });
});

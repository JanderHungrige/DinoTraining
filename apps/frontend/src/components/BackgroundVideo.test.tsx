import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { LookProvider } from '../lib/look';
import { AppearancePanel } from './AppearancePanel';
import { BackgroundVideo, POSTER_SRC } from './BackgroundVideo';

let reduceMotion = false;
const listeners = new Set<() => void>();

beforeEach(() => {
  reduceMotion = false;
  vi.stubGlobal('matchMedia', (query: string) => ({
    get matches() {
      return query.includes('reduce') && reduceMotion;
    },
    addEventListener: (_: string, cb: () => void) => listeners.add(cb),
    removeEventListener: (_: string, cb: () => void) => listeners.delete(cb),
  }));
  // jsdom implements no media playback.
  vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue(undefined);
  vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  listeners.clear();
});

function layer(): HTMLElement {
  return document.querySelector('.bgvideo') as HTMLElement;
}

describe('BackgroundVideo (doc 77)', () => {
  it('plays the loop, muted and looping, hidden from assistive tech', () => {
    render(
      <LookProvider>
        <BackgroundVideo />
      </LookProvider>,
    );
    const video = layer().querySelector('video')!;
    expect(video.muted).toBe(true);
    expect(video.loop).toBe(true);
    expect(video.getAttribute('src')).toContain('background/particles-loop.mp4');
    expect(layer()).toHaveAttribute('aria-hidden', 'true');
  });

  it('shows the still poster when the system asks for reduced motion, and follows it live', () => {
    reduceMotion = true;
    render(
      <LookProvider>
        <BackgroundVideo />
      </LookProvider>,
    );
    expect(layer().querySelector('video')).toBeNull();
    expect(layer().querySelector('img')).toHaveAttribute('src', POSTER_SRC);

    reduceMotion = false;
    act(() => listeners.forEach((cb) => cb()));
    expect(layer().querySelector('video')).not.toBeNull();
  });

  it("Admin's switch turns it off on screen, not just in storage", async () => {
    // Two components, one preference: the reason the look lives in a context.
    const user = userEvent.setup();
    render(
      <LookProvider>
        <BackgroundVideo />
        <AppearancePanel />
      </LookProvider>,
    );
    await user.click(screen.getByRole('checkbox', { name: /animated background/i }));
    expect(layer().querySelector('video')).toBeNull();
    expect(localStorage.getItem('dinotraining.v1.look.animatedBackground')).toBe('false');
  });

  it('pauses while the window is hidden and resumes when it is shown', () => {
    render(
      <LookProvider>
        <BackgroundVideo />
      </LookProvider>,
    );
    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
    document.dispatchEvent(new Event('visibilitychange'));
    expect(HTMLMediaElement.prototype.pause).toHaveBeenCalled();

    hidden.mockReturnValue(false);
    document.dispatchEvent(new Event('visibilitychange'));
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled();
  });
});

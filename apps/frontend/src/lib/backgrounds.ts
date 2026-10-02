/**
 * The backgrounds a user can choose in Settings (doc 165).
 *
 * Jan (2026-10-02): "put all versions into Settings; the user decides what they like".
 * Each one brings its own treatment, so it looks the way it was tried: the scrim and the
 * panels' blur are set per background in look.css (`:root[data-background=…]`).
 *
 * The default keeps the old file names (`particles-loop.mp4`, `particles-poster.jpg`):
 * the download site's updater copies exactly those, so the site shows the default too.
 */

import type { Key } from '../i18n';

export const BACKGROUNDS = ['forest', 'forest-sharp', 'forest-bright', 'forest-dim', 'particles'] as const;
export type BackgroundId = (typeof BACKGROUNDS)[number];
export const DEFAULT_BACKGROUND: BackgroundId = 'forest';

interface Background {
  readonly label: Key;
  readonly video: string;
  readonly poster: string;
}

const BASE = `${import.meta.env.BASE_URL}background/`;

export const BACKGROUND: Readonly<Record<BackgroundId, Background>> = {
  forest: { label: 'app.appearance.bg.forest', video: 'particles-loop.mp4', poster: 'particles-poster.jpg' },
  'forest-sharp': { label: 'app.appearance.bg.forestSharp', video: 'forest-sharp.mp4', poster: 'forest-sharp-poster.jpg' },
  'forest-bright': { label: 'app.appearance.bg.forestBright', video: 'forest-bright.mp4', poster: 'forest-bright-poster.jpg' },
  'forest-dim': { label: 'app.appearance.bg.forestDim', video: 'forest-dim.mp4', poster: 'forest-dim-poster.jpg' },
  particles: { label: 'app.appearance.bg.particles', video: 'original-particles.mp4', poster: 'original-particles-poster.jpg' },
};

export function backgroundVideo(id: BackgroundId): string {
  return BASE + BACKGROUND[id].video;
}

export function backgroundPoster(id: BackgroundId): string {
  return BASE + BACKGROUND[id].poster;
}

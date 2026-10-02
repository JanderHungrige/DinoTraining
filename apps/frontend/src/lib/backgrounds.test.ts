import { describe, expect, it } from 'vitest';

import { BACKGROUND, BACKGROUNDS, DEFAULT_BACKGROUND } from './backgrounds';

// Only the names: a glob without `eager` loads nothing.
const shipped = Object.keys(import.meta.glob('../../public/background/*')).map((path) => path.split('/').pop());

describe('the backgrounds (doc 165)', () => {
  it('ship every file they name', () => {
    for (const id of BACKGROUNDS) {
      expect(shipped, id).toContain(BACKGROUND[id].video);
      expect(shipped, id).toContain(BACKGROUND[id].poster);
    }
  });

  it('keep the default in the files the download site copies', () => {
    expect(BACKGROUND[DEFAULT_BACKGROUND]).toMatchObject({ video: 'particles-loop.mp4', poster: 'particles-poster.jpg' });
  });

  it('ship nothing that no background uses', () => {
    const used = new Set(BACKGROUNDS.flatMap((id) => [BACKGROUND[id].video, BACKGROUND[id].poster]));
    expect(shipped.filter((name) => name && /\.(mp4|jpg)$/.test(name) && !used.has(name))).toEqual([]);
  });
});

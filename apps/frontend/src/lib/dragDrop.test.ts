/**
 * Desktop file drops (doc 40).
 *
 * `folderOf` gets most of the attention because it is the one piece with a judgement in it:
 * the Studio and the Generator take a **folder**, but people drop the images they can see.
 * Deciding by extension is a deliberate trade — the frontend has no `stat` and a round trip
 * would make a drop feel slow — so the edges are worth pinning.
 */

import { afterEach, describe, expect, it, vi } from 'vitest';

import { folderOf, hasFileDrop, listenForFileDrop } from './dragDrop';

afterEach(() => {
  vi.unstubAllGlobals();
  Reflect.deleteProperty(window, '__TAURI_INTERNALS__');
});

describe('folderOf', () => {
  it('returns a folder path unchanged', () => {
    expect(folderOf('/Users/jan/photos')).toBe('/Users/jan/photos');
  });

  it('returns the parent of a dropped image', () => {
    // The case this exists for: dropping one visible image and being told "not a folder"
    // is a worse answer than doing the obvious thing.
    expect(folderOf('/Users/jan/photos/cat.jpg')).toBe('/Users/jan/photos');
  });

  it('is case-insensitive about the extension', () => {
    expect(folderOf('/Users/jan/photos/CAT.JPG')).toBe('/Users/jan/photos');
  });

  it('handles every extension the backend accepts', () => {
    for (const extension of ['jpg', 'jpeg', 'png', 'bmp', 'webp', 'tif', 'tiff', 'gif']) {
      expect(folderOf(`/pics/a.${extension}`)).toBe('/pics');
    }
  });

  it('leaves a non-image file alone', () => {
    // Not an image, so not something we can infer a folder from — pass it through and let
    // the backend say what is wrong with it.
    expect(folderOf('/Users/jan/notes.txt')).toBe('/Users/jan/notes.txt');
  });

  it('leaves a folder with a dot in its name alone', () => {
    expect(folderOf('/Users/jan/photos.backup')).toBe('/Users/jan/photos.backup');
  });

  it('leaves a dotfile alone', () => {
    // The dot is at index 0, which is a hidden file rather than an extension.
    expect(folderOf('/Users/jan/.hidden')).toBe('/Users/jan/.hidden');
  });

  it('handles Windows separators', () => {
    expect(folderOf('C:\\Users\\jan\\photos\\cat.png')).toBe('C:\\Users\\jan\\photos');
  });

  it('returns the root for an image at the root', () => {
    // The parent of `/cat.jpg` is the empty string, which is not a path.
    expect(folderOf('/cat.jpg')).toBe('/');
  });

  it('keeps a path with no separator at all', () => {
    expect(folderOf('photos')).toBe('photos');
  });
});

describe('availability', () => {
  it('reports no drops in a browser', () => {
    expect(hasFileDrop()).toBe(false);
  });

  it('reports drops inside Tauri', () => {
    vi.stubGlobal('window', Object.assign(window, { __TAURI_INTERNALS__: {} }));
    expect(hasFileDrop()).toBe(true);
  });

  it('subscribing outside Tauri is a harmless no-op', async () => {
    // Callers wire this up unconditionally; making them each check first is how one of
    // them eventually forgets.
    const onDrop = vi.fn();
    const stop = await listenForFileDrop({ onDrop });

    expect(onDrop).not.toHaveBeenCalled();
    expect(() => stop()).not.toThrow();
  });
});

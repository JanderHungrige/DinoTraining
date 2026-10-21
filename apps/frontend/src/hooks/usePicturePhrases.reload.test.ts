/** Jan (2026-10-21): new classes only became phrases for "+ Umbrella term" after a reopen. */
import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as api from '../api/phrases';
import { usePicturePhrases } from './usePicturePhrases';

vi.mock('../api/phrases', async () => {
  const actual = await vi.importActual<typeof import('../api/phrases')>('../api/phrases');
  return { ...actual, listPhrases: vi.fn(), pictureStatuses: vi.fn() };
});

beforeEach(() => {
  vi.mocked(api.listPhrases).mockReset().mockResolvedValue([]);
  vi.mocked(api.pictureStatuses).mockReset().mockResolvedValue([]);
});

const calls = (): number => vi.mocked(api.listPhrases).mock.calls.length;

describe('the phrase list follows the annotation list', () => {
  it('is read again when a picture is saved (unsaved turns clean)', async () => {
    const { rerender } = renderHook(({ dirty }) => usePicturePhrases('d1', '/a.jpg', dirty), {
      initialProps: { dirty: false },
    });
    await waitFor(() => expect(calls()).toBe(1));
    rerender({ dirty: true }); // a class made in the annotation list
    expect(calls()).toBe(1);
    rerender({ dirty: false }); // saved
    await waitFor(() => expect(calls()).toBe(2));
  });

  it('is read again on the next picture', async () => {
    const { rerender } = renderHook(({ path }) => usePicturePhrases('d1', path), {
      initialProps: { path: '/a.jpg' },
    });
    await waitFor(() => expect(calls()).toBe(1));
    rerender({ path: '/b.jpg' });
    await waitFor(() => expect(calls()).toBe(2));
  });
});

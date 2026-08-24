/**
 * The CanvasBox -> API box translation in `saveImageBoxes`.
 *
 * This file exists because of one bug that only the running app could surface: the canvas
 * calls a box's class `text`, the store calls it `prompt`, and nothing renamed it on the
 * way out. Pydantic drops unknown fields silently, so every save succeeded, every counter
 * was right, and the class name was simply gone. See 31-external-dataset-import.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { CanvasBox } from '../types/annotation';
import { saveImageBoxes } from './datasets';

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
  fetchMock.mockResolvedValue(
    new Response(
      JSON.stringify({
        images: 1,
        boxes: 1,
        masks: 0,
        positive: 1,
        negative: 0,
        unclear: 0,
      }),
      { status: 200, headers: { 'Content-Type': 'application/json' } },
    ),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  // restoreAllMocks does not clear vi.fn() call history — only spies. Without this a
  // later test reads a previous test's calls and appears to prove something it did not.
  vi.clearAllMocks();
});

const IMAGE = { path: '/images/a.jpg', width: 200, height: 100 };

function canvasBox(overrides: Partial<CanvasBox> = {}): CanvasBox {
  return {
    id: 'expert-0',
    label: 'positive',
    provenance: 'expert-head',
    x: 10,
    y: 20,
    w: 30,
    h: 40,
    ...overrides,
  };
}

async function sentBoxes(boxes: readonly CanvasBox[]): Promise<Record<string, unknown>[]> {
  await saveImageBoxes('d1', IMAGE, boxes);
  const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
  return body.boxes as Record<string, unknown>[];
}

describe('saveImageBoxes', () => {
  it("renames the canvas's `text` to the store's `prompt`", async () => {
    const [sent] = await sentBoxes([canvasBox({ text: 'person' })]);
    expect(sent?.['prompt']).toBe('person');
  });

  it('does not send `text`, which the backend would silently discard', async () => {
    const [sent] = await sentBoxes([canvasBox({ text: 'person' })]);
    expect(sent).not.toHaveProperty('text');
  });

  it('keeps each box\'s own class rather than collapsing them', async () => {
    // The flywheel case: a detector proposes several classes over one image, and the
    // dataset that results has to be able to train the next head on those same classes.
    const sent = await sentBoxes([
      canvasBox({ id: 'a', text: 'dog' }),
      canvasBox({ id: 'b', text: 'person' }),
    ]);
    expect(sent.map((box) => box['prompt'])).toEqual(['dog', 'person']);
  });

  it('omits `prompt` entirely for a box with no class', async () => {
    // Hand-drawn boxes carry no text. Sending prompt:"" would store an empty string as a
    // class name, which `build_class_vocabulary` would then treat as a real class.
    const [sent] = await sentBoxes([canvasBox()]);
    expect(sent).not.toHaveProperty('prompt');
  });

  it('still strips the client-side id', async () => {
    const [sent] = await sentBoxes([canvasBox({ text: 'person' })]);
    expect(sent).not.toHaveProperty('id');
  });

  it('preserves the fields the store does want', async () => {
    const [sent] = await sentBoxes([
      canvasBox({ text: 'person', score: 0.87, producer: { id: 'h1', label: 'A head' } }),
    ]);
    expect(sent).toMatchObject({
      label: 'positive',
      provenance: 'expert-head',
      x: 10,
      y: 20,
      w: 30,
      h: 40,
      score: 0.87,
      producer: { id: 'h1', label: 'A head' },
    });
  });

  it('sends the image-level prompt as null when there is none', async () => {
    // The Dataset Generator has no phrase to send — it ran a head. That is exactly why
    // the backend's `box.prompt or annotation.prompt` fallback could not rescue it.
    await saveImageBoxes('d1', IMAGE, [canvasBox({ text: 'person' })]);
    const body = JSON.parse(String(fetchMock.mock.calls[0]?.[1]?.body));
    expect(body.prompt).toBeNull();
  });
});

/** Shared fixtures for the useAnnotationSession tests. Not a test file itself. */

import { vi } from 'vitest';

import type { CanvasBox } from '../types/annotation';
import type { SessionConfig } from './useAnnotationSession';

export const CONFIG: SessionConfig = {
  images: { kind: 'folder', folder: '/pics' },
  datasetId: 'ds1',
  source: { kind: 'prompt', prompt: 'a cat', boxThreshold: 0.3, textThreshold: 0.25 },
};

/** The same session, proposing from a trained head instead of a phrase. */
export const HEAD_CONFIG: SessionConfig = {
  images: { kind: 'folder', folder: '/pics' },
  datasetId: 'ds1',
  source: {
    kind: 'head',
    backboneId: 'dinov2-small',
    instanceId: 'h1',
    scoreThreshold: 0.3,
  },
};

export const IMAGES = ['/pics/a.jpg', '/pics/b.jpg', '/pics/c.jpg'];

export const COUNTS = { images: 1, boxes: 2, positive: 1, negative: 1, unclear: 0 };

export const PROPOSAL = {
  image_path: '/pics/a.jpg',
  width: 200,
  height: 100,
  prompt: 'a cat',
  device: 'cpu',
  boxes: [
    {
      label: 'positive',
      provenance: 'grounding-dino',
      x: 1,
      y: 2,
      w: 3,
      h: 4,
      score: 0.9,
      text: 'a cat',
    },
  ],
};

/** What `POST /generate/expert` returns — a head's proposals, not a phrase's. */
export const EXPERT_PROPOSAL = {
  image_path: '/pics/a.jpg',
  width: 200,
  height: 100,
  device: 'mps',
  head_name: 'Thermal spotter',
  head_summary: 'Object detection · 2 classes · trained on 1 dataset · map 0.403',
  boxes: [
    {
      label: 'positive',
      provenance: 'expert-head',
      x: 5,
      y: 6,
      w: 7,
      h: 8,
      score: 0.87,
      prompt: 'person',
      producer: { id: 'h1', label: 'Thermal spotter' },
    },
  ],
};

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export interface Handlers {
  folder?: () => Response;
  annotate?: () => Response;
  expert?: () => Response;
  save?: () => Response;
}

/** Route by URL and method so the hook's real call sequence is exercised. */
export function route(fetchMock: ReturnType<typeof vi.fn>, handlers: Handlers = {}): void {
  fetchMock.mockImplementation((input: unknown, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/annotate/folder')) {
      return Promise.resolve(
        (handlers.folder ?? (() => json({ folder: '/pics', images: IMAGES })))(),
      );
    }
    if (url.includes('/generate/expert')) {
      return Promise.resolve((handlers.expert ?? (() => json(EXPERT_PROPOSAL)))());
    }
    if (url.includes('/annotate')) {
      return Promise.resolve((handlers.annotate ?? (() => json(PROPOSAL)))());
    }
    if (init?.method === 'PUT') {
      return Promise.resolve((handlers.save ?? (() => json(COUNTS)))());
    }
    return Promise.resolve(json({}));
  });
}

export function box(overrides: Partial<CanvasBox> = {}): CanvasBox {
  return {
    id: 'x1',
    label: 'positive',
    provenance: 'hand-drawn',
    x: 0,
    y: 0,
    w: 10,
    h: 10,
    ...overrides,
  };
}

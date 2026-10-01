import { renderHook } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { SessionConfig } from './useAnnotationSession';
import { usePromptClasses } from './usePromptClasses';

vi.mock('../api/datasetClasses', () => ({ createDatasetClass: vi.fn(async () => []) }));
const api = await import('../api/datasetClasses');

const prompt = (text: string): SessionConfig =>
  ({
    datasetId: 'd1',
    source: { kind: 'prompt', prompt: text, boxThreshold: 0.3, textThreshold: 0.25 },
  }) as unknown as SessionConfig;

describe('usePromptClasses (doc 117)', () => {
  it('stores every prompt term as a class when the session starts', () => {
    renderHook(() => usePromptClasses(prompt('m8, m9. m10')));
    expect(vi.mocked(api.createDatasetClass).mock.calls.map((c) => c[1])).toEqual(['m8', 'm9', 'm10']);
  });

  it('does nothing without a prompt source', () => {
    vi.mocked(api.createDatasetClass).mockClear();
    renderHook(() => usePromptClasses(null));
    expect(api.createDatasetClass).not.toHaveBeenCalled();
  });
});

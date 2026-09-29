import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { StoredBox } from '../api/datasets';
import { asPrediction, StoredOverlay } from './StoredOverlay';

const RENDERED = { width: 100, height: 100, offsetX: 0, offsetY: 0, naturalWidth: 100, naturalHeight: 100 };

function box(label: StoredBox['label'], prompt: string): StoredBox {
  return { label, provenance: 'hand-drawn', x: 1, y: 1, w: 5, h: 5, prompt } as StoredBox;
}

describe('StoredOverlay (doc 74)', () => {
  it('colours by class, with one index per class across the dataset', () => {
    const prediction = asPrediction(
      [
        { x: 0, y: 0, w: 1, h: 1, name: 'train' },
        { x: 0, y: 0, w: 1, h: 1, name: 'signal' },
        { x: 0, y: 0, w: 1, h: 1, name: 'unknown' },
      ],
      ['signal', 'train'],
    );
    expect(prediction.payload['classes']).toEqual([1, 0, 2]);
    expect(prediction.class_names).toEqual(['signal', 'train', 'unnamed']);
  });

  it('draws what the dataset asserts — positives, not rejected or unclear proposals', () => {
    const { container } = render(
      <StoredOverlay
        boxes={[box('positive', 'signal'), box('negative', 'signal'), box('unclear', 'train')]}
        masks={[]}
        classNames={['signal', 'train']}
        width={100}
        height={100}
        rendered={RENDERED}
        view="both"
      />,
    );
    expect(container.querySelectorAll('.overlay__box')).toHaveLength(1);
  });

  it('draws nothing on a frame with nothing on it', () => {
    const { container } = render(
      <StoredOverlay
        boxes={[]}
        masks={[]}
        classNames={[]}
        width={100}
        height={100}
        rendered={RENDERED}
        view="masks"
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});

/**
 * The view rules (doc 67).
 *
 * Small functions, but they encode the two decisions the feature rests on: that "boxes
 * only" is reachable at all, and that what gets *saved* is a fact to be stated rather than
 * a choice to be offered.
 */

import { describe, expect, it } from 'vitest';

import {
  DEFAULT_VIEW,
  describeOutput,
  showsBoxes,
  showsMasks,
  viewsFor,
  VIEW_LABELS,
} from './annotationView';

describe('what each view draws', () => {
  it('masks draws the mask and not the box', () => {
    expect(showsMasks('masks')).toBe(true);
    expect(showsBoxes('masks')).toBe(false);
  });

  it('boxes draws the box and not the mask', () => {
    // The state the Studio's old boolean could not reach: with `showBoxes` false the mask
    // was on, and with it true both were — so "box alone" did not exist.
    expect(showsMasks('boxes')).toBe(false);
    expect(showsBoxes('boxes')).toBe(true);
  });

  it('both draws both', () => {
    expect(showsMasks('both')).toBe(true);
    expect(showsBoxes('both')).toBe(true);
  });

  it('every view draws something', () => {
    // A view that renders nothing is indistinguishable from a model that found nothing.
    for (const view of ['masks', 'boxes', 'both'] as const) {
      expect(showsMasks(view) || showsBoxes(view)).toBe(true);
    }
  });
});

describe('which views are offered', () => {
  it('offers all three when the result has both', () => {
    expect(viewsFor(true, true)).toEqual(['masks', 'boxes', 'both']);
  });

  it('offers only boxes for a box-only result', () => {
    // RF-DETR and Grounding DINO have no mask. Offering a disabled "Segmentation" option
    // invites the reader to wonder what they did wrong.
    expect(viewsFor(false, true)).toEqual(['boxes']);
  });

  it('offers only masks when there are no boxes', () => {
    expect(viewsFor(true, false)).toEqual(['masks']);
  });

  it('offers nothing for an empty result', () => {
    expect(viewsFor(false, false)).toEqual([]);
  });

  it('defaults to the mask, which is the finer answer', () => {
    expect(DEFAULT_VIEW).toBe('masks');
    expect(viewsFor(true, true)[0]).toBe(DEFAULT_VIEW);
  });

  it('labels every view it can offer', () => {
    // A missing label renders an empty radio, which is a control with no meaning.
    for (const view of viewsFor(true, true)) {
      expect(VIEW_LABELS[view]).toBeTruthy();
    }
  });
});

describe('what a model saves', () => {
  it('says a mask model saves masks — and boxes too', () => {
    // The correction that produced this feature: bounding boxes come out of a segmentation
    // run anyway, because the exporter derives one from each mask. Someone who does not
    // know that reasonably asks for a "both" option that would double every object.
    const sentence = describeOutput('masks');

    expect(sentence).toMatch(/segmentation masks/i);
    expect(sentence).toMatch(/bounding box/i);
  });

  it('says a box model saves boxes', () => {
    expect(describeOutput('boxes')).toMatch(/bounding boxes/i);
  });

  it('does not claim masks for a box model', () => {
    expect(describeOutput('boxes')).not.toMatch(/segmentation/i);
  });

  it('says nothing for a model that saves nothing', () => {
    // Depth writes no annotations. A confident sentence about what it saves would be false.
    expect(describeOutput('depth-map')).toBe('');
  });

  it('is keyed on the render hint, not on a model id', () => {
    // Grounded SAM, SAM 3 and a fine-tuned RF-DETR share no id pattern, and the next model
    // will share one with nothing. Same rule doc 66 applied to `takes_concept`.
    expect(describeOutput('masks')).toBe(describeOutput('masks'));
    expect(describeOutput('unknown-hint')).toBe('');
  });
});

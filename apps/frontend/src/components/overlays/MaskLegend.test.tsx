/**
 * Naming the colours on a segmentation.
 *
 * `present_classes` had been on the wire since Wave 3 and read by nothing, so a
 * segmentation was coloured regions with no key. Once ADE20k's names are carried, leaving
 * it unread would mean supplying the names and never showing them.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { Prediction } from '../../api/inference';
import { legendEntries, MaskLegend } from './MaskLegend';

function prediction(
  present: unknown,
  classNames: readonly string[] = ['wall', 'building', 'sky', 'floor', 'tree'],
): Prediction {
  return {
    instance_id: 'h1',
    head_name: 'DINOv2 linear segmenter (ADE20k)',
    head_type_id: 'dinov2-linear-segmenter-ade20k',
    task: 'segmentation',
    render_hint: 'masks',
    class_names: classNames,
    payload: { present_classes: present, mask_png: 'x', class_stride: 42 },
    elapsed_ms: 10,
  } as unknown as Prediction;
}

describe('what it names', () => {
  it('names the classes the model actually found', () => {
    render(<MaskLegend prediction={prediction([0, 4])} />);

    expect(screen.getByText('wall')).toBeInTheDocument();
    expect(screen.getByText('tree')).toBeInTheDocument();
  });

  it('lists only what is present, not the whole label set', () => {
    // ADE20k has 150 classes and a frame holds five or six. A full key would bury the
    // answer in 144 lines of things that are not in the picture.
    render(<MaskLegend prediction={prediction([2])} />);

    expect(screen.getAllByRole('listitem')).toHaveLength(1);
    expect(screen.queryByText('building')).not.toBeInTheDocument();
  });

  it('treats present_classes as indices, not as pixel values', () => {
    // The map's *pixels* are index × class_stride; `present_classes` is already the index.
    // Dividing by the stride here would collapse every class to 0 and label the whole
    // image "wall" — plausible, wrong, and silent.
    render(<MaskLegend prediction={prediction([4])} />);

    expect(screen.getByText('tree')).toBeInTheDocument();
    expect(screen.queryByText('wall')).not.toBeInTheDocument();
  });

  it('caps a long list rather than out-growing the image', () => {
    const entries = legendEntries(
      prediction(
        Array.from({ length: 20 }, (_, i) => i),
        Array.from({ length: 20 }, (_, i) => `class-${i}`),
      ),
    );

    expect(entries).toHaveLength(8);
  });
});

describe('what it leaves out', () => {
  it('omits a named background', () => {
    // Background is the absence of a finding, drawn transparent. A swatch for it is an
    // invisible colour beside the word "background".
    render(
      <MaskLegend prediction={prediction([0, 1], ['background', 'a red circle'])} />,
    );

    expect(screen.queryByText('background')).not.toBeInTheDocument();
    expect(screen.getByText('a red circle')).toBeInTheDocument();
  });

  it('renders nothing when the model found nothing', () => {
    const { container } = render(<MaskLegend prediction={prediction([])} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when the payload has no present_classes', () => {
    const { container } = render(<MaskLegend prediction={prediction(undefined)} />);

    expect(container).toBeEmptyDOMElement();
  });

  it('survives a payload that is not a list', () => {
    // Defensive because the field went years without a reader; nothing guaranteed its shape.
    const { container } = render(<MaskLegend prediction={prediction('all of them')} />);

    expect(container).toBeEmptyDOMElement();
  });
});

describe('a head whose names are unknown', () => {
  it('falls back to the index rather than an empty row', () => {
    render(<MaskLegend prediction={prediction([7], [])} />);

    expect(screen.getByText('class 7')).toBeInTheDocument();
  });
});

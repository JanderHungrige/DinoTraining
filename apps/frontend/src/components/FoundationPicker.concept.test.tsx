/**
 * Concept-prompted models in the box pickers (doc 45).
 *
 * The two things that fail quietly: a concept segmenter being filtered out of a surface
 * that *can* review its boxes, and its concept field lingering after the user switches
 * back to a detector that ignores it.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { FoundationInfo } from '../api/foundation';
import { FoundationPicker } from './FoundationPicker';

const DETECTOR: FoundationInfo = {
  id: 'rf-detr-nano',
  title: 'RF-DETR (nano)',
  description: 'General object detection, 91 COCO classes.',
  task: 'detection',
  render_hint: 'boxes',
  model_id: 'rf-detr-nano',
  licence: 'Apache-2.0',
  non_commercial: false,
  installed: true,
  approx_size_mb: 116,
  takes_concept: false,
};

const CONCEPT: FoundationInfo = {
  ...DETECTOR,
  id: 'grounded-sam',
  title: 'Grounded SAM',
  description: 'Segments whatever you name.',
  task: 'segmentation',
  render_hint: 'masks',
  takes_concept: true,
};

const DEPTH: FoundationInfo = {
  ...DETECTOR,
  id: 'depth-anything-v2-small',
  title: 'Depth Anything V2',
  task: 'depth',
  render_hint: 'depth-map',
};

function renderPicker(props: Partial<Parameters<typeof FoundationPicker>[0]> = {}) {
  const onSelect = vi.fn();
  const onConceptChange = vi.fn();
  render(
    <FoundationPicker
      foundations={[DETECTOR, CONCEPT, DEPTH]}
      selectedId="rf-detr-nano"
      onSelect={onSelect}
      onConceptChange={onConceptChange}
      {...props}
    />,
  );
  return { onSelect, onConceptChange, user: userEvent.setup() };
}

describe('what is offered', () => {
  it('offers a concept segmenter even though it renders masks', () => {
    // `render_hint` alone stopped answering "can this be reviewed as boxes?" at doc 45:
    // Grounding DINO found boxes on the way to those masks.
    renderPicker();
    expect(screen.getByRole('radio', { name: /Grounded SAM/ })).toBeInTheDocument();
  });

  it('still refuses a depth model', () => {
    // The rule widened; it did not dissolve. There is nothing to review a depth map with.
    renderPicker();
    expect(screen.queryByRole('radio', { name: /Depth Anything/ })).not.toBeInTheDocument();
  });
});

describe('the concept field', () => {
  it('is hidden while a detector is selected', () => {
    // RF-DETR predicts its 91 COCO classes whatever is typed at it. A field that does
    // nothing is worse than no field.
    renderPicker();
    expect(screen.queryByLabelText(/What to find/)).not.toBeInTheDocument();
  });

  it('appears when a concept segmenter is selected', () => {
    renderPicker({ selectedId: 'grounded-sam' });
    expect(screen.getByLabelText(/What to find/)).toBeInTheDocument();
  });

  it('reports what was typed', async () => {
    const { onConceptChange, user } = renderPicker({ selectedId: 'grounded-sam' });
    await user.type(screen.getByLabelText(/What to find/), 'c');
    expect(onConceptChange).toHaveBeenCalledWith('c');
  });

  it('stays hidden on a surface that owns its own prompt field', () => {
    // The Generator already has one. Two inputs for one string is how they drift apart.
    render(
      <FoundationPicker
        foundations={[CONCEPT]}
        selectedId="grounded-sam"
        onSelect={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText(/What to find/)).not.toBeInTheDocument();
  });

  it('names the model it belongs to', () => {
    renderPicker({ selectedId: 'grounded-sam' });
    expect(screen.getByText(/Grounded SAM finds only what you name/)).toBeInTheDocument();
  });
});

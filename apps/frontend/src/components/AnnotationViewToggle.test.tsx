/**
 * The shared view control (doc 67).
 *
 * What matters is what it refuses to render. A control offering one option, or offering
 * "Segmentation" for a result that has no mask, is worse than no control — it implies a
 * choice that does not exist and invites the reader to hunt for the missing half.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { AnnotationViewToggle } from './AnnotationViewToggle';

describe('when a result has both', () => {
  it('offers all three', () => {
    render(
      <AnnotationViewToggle view="masks" onChange={vi.fn()} hasMasks hasBoxes />,
    );

    expect(screen.getByRole('radio', { name: 'Segmentation' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Bounding boxes' })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: 'Both' })).toBeInTheDocument();
  });

  it('marks the current view', () => {
    render(<AnnotationViewToggle view="both" onChange={vi.fn()} hasMasks hasBoxes />);

    expect(screen.getByRole('radio', { name: 'Both' })).toBeChecked();
    expect(screen.getByRole('radio', { name: 'Segmentation' })).not.toBeChecked();
  });

  it('reports a change', async () => {
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<AnnotationViewToggle view="masks" onChange={onChange} hasMasks hasBoxes />);

    await user.click(screen.getByRole('radio', { name: 'Bounding boxes' }));

    expect(onChange).toHaveBeenCalledWith('boxes');
  });

  it('can reach boxes-only, which the old checkbox could not', async () => {
    // The Studio's `showBoxes` boolean drew the mask either way. "Box alone" — the view
    // for checking extents against a detector — had no representation at all.
    const onChange = vi.fn();
    const user = userEvent.setup();
    render(<AnnotationViewToggle view="both" onChange={onChange} hasMasks hasBoxes />);

    await user.click(screen.getByRole('radio', { name: 'Bounding boxes' }));

    expect(onChange).toHaveBeenCalledWith('boxes');
  });
});

describe('when there is nothing to choose between', () => {
  it('renders nothing for a box-only result', () => {
    // RF-DETR and Grounding DINO. One radio is not a choice.
    const { container } = render(
      <AnnotationViewToggle view="boxes" onChange={vi.fn()} hasMasks={false} hasBoxes />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing for a mask-only result', () => {
    const { container } = render(
      <AnnotationViewToggle view="masks" onChange={vi.fn()} hasMasks hasBoxes={false} />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing for an empty result', () => {
    const { container } = render(
      <AnnotationViewToggle
        view="masks"
        onChange={vi.fn()}
        hasMasks={false}
        hasBoxes={false}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});

describe('two on one page', () => {
  it('keeps its radios separate from another group', () => {
    // Same `name` would make selecting a view in one panel clear the other's.
    render(
      <>
        <AnnotationViewToggle
          view="masks"
          onChange={vi.fn()}
          hasMasks
          hasBoxes
          groupName="left"
        />
        <AnnotationViewToggle
          view="boxes"
          onChange={vi.fn()}
          hasMasks
          hasBoxes
          groupName="right"
        />
      </>,
    );

    const checked = screen.getAllByRole('radio').filter((radio) => (radio as HTMLInputElement).checked);
    expect(checked).toHaveLength(2);
  });
});

describe('while a run is in flight', () => {
  it('disables every option rather than half of them', () => {
    render(
      <AnnotationViewToggle view="masks" onChange={vi.fn()} hasMasks hasBoxes disabled />,
    );

    for (const radio of screen.getAllByRole('radio')) {
      expect(radio).toBeDisabled();
    }
  });
});

/**
 * The viewer is layout only — these tests exist mostly to hold that line.
 *
 * If a future change makes this component aware of what a head produced, the
 * "same transform on both panes" test is what will still pass while the design has
 * quietly broken, so the boundary is asserted directly too.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { SideBySideViewer } from './SideBySideViewer';

function transformOf(element: HTMLElement): string {
  return element.style.transform;
}

function stages(): HTMLElement[] {
  return screen.getAllByTestId('viewer-stage');
}

describe('SideBySideViewer', () => {
  it('shows the same image in both panes', () => {
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);

    const images = screen.getAllByRole('img');
    expect(images).toHaveLength(2);
    expect(images.every((img) => img.getAttribute('src') === '/img/cat.png')).toBe(true);
  });

  it('labels the panes so the two are distinguishable', () => {
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);

    expect(screen.getByText(/original/i)).toBeInTheDocument();
    expect(screen.getByText(/result/i)).toBeInTheDocument();
  });

  it('applies one identical transform to both panes', () => {
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);

    fireEvent.click(screen.getByRole('button', { name: /zoom in/i }));

    const [left, right] = stages();
    expect(left).toBeDefined();
    expect(transformOf(left as HTMLElement)).not.toBe('');
    expect(transformOf(left as HTMLElement)).toBe(transformOf(right as HTMLElement));
  });

  it('resets to fit', () => {
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);

    fireEvent.click(screen.getByRole('button', { name: /zoom in/i }));
    const zoomed = transformOf(stages()[0] as HTMLElement);
    fireEvent.click(screen.getByRole('button', { name: /reset/i }));

    expect(transformOf(stages()[0] as HTMLElement)).not.toBe(zoomed);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('cannot zoom out below fit', () => {
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);

    fireEvent.click(screen.getByRole('button', { name: /zoom out/i }));

    expect(screen.getByText('100%')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /zoom out/i })).toBeDisabled();
  });

  it('is operable from the keyboard', () => {
    // Wheel-only zoom is unusable without a mouse and invisible to anyone who does not
    // think to try it.
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);
    const region = screen.getByRole('group', { name: /image comparison/i });

    fireEvent.keyDown(region, { key: '+' });
    expect(screen.queryByText('100%')).toBeNull();

    fireEvent.keyDown(region, { key: '0' });
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('renders the overlay in the result pane only', () => {
    render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        results={[{ key: 'r', label: 'Result', renderOverlay: () => <div data-testid="overlay">marks</div> }]}
      />,
    );

    const overlays = screen.getAllByTestId('overlay');
    expect(overlays).toHaveLength(1);
    // ...and inside the right-hand stage, so the transform carries it.
    expect(stages()[1]?.contains(overlays[0] as Node)).toBe(true);
  });

  it('hands the overlay the rendered image geometry, not the container box', () => {
    // A letterboxed image is not its container; positioning from the container offsets
    // every mark by the letterbox.
    const renderOverlay = vi.fn().mockReturnValue(null);
    render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        naturalWidth={900}
        naturalHeight={300}
        results={[{ key: 'r', label: 'Result', renderOverlay }]}
      />,
    );

    expect(renderOverlay).toHaveBeenCalled();
    const rendered = renderOverlay.mock.calls[0]?.[0];
    expect(rendered).toMatchObject({ naturalWidth: 900, naturalHeight: 300 });
    expect(rendered).toHaveProperty('offsetX');
    expect(rendered).toHaveProperty('width');
  });

  it('does not reset when a control is double-clicked', () => {
    // Found in the browser: with the handler on the outer container, clicking "Zoom in"
    // twice quickly — an entirely natural thing to do — bubbled a dblclick and threw the
    // zoom away.
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);
    const zoomIn = screen.getByRole('button', { name: /zoom in/i });

    fireEvent.click(zoomIn);
    fireEvent.click(zoomIn);
    fireEvent.doubleClick(zoomIn);

    expect(screen.queryByText('100%')).toBeNull();
  });

  it('does reset when the image itself is double-clicked', () => {
    render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);

    fireEvent.click(screen.getByRole('button', { name: /zoom in/i }));
    fireEvent.doubleClick(screen.getAllByTestId('viewer-frame')[0] as HTMLElement);

    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('clamps against the pane frame, not the whole component', () => {
    // Also found in the browser: the component is roughly twice a pane's width, so
    // measuring it gave pan bounds twice too generous and the image could be dragged
    // off its own frame. jsdom reports every element as 0x0, so sizes are stubbed
    // *before* mount — the measurement happens in a mount effect.
    const widths = vi
      .spyOn(HTMLElement.prototype, 'clientWidth', 'get')
      .mockReturnValue(300);
    const heights = vi
      .spyOn(HTMLElement.prototype, 'clientHeight', 'get')
      .mockReturnValue(200);

    try {
      render(<SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" />);
      const frame = screen.getAllByTestId('viewer-frame')[0] as HTMLElement;
      fireEvent.click(screen.getByRole('button', { name: /zoom in/i }));

      // Drag far further than the content can travel, then read where it stopped.
      fireEvent.pointerDown(frame, { clientX: 0, clientY: 0, pointerId: 1 });
      fireEvent.pointerMove(frame, { clientX: -5000, clientY: -5000, pointerId: 1 });
      fireEvent.pointerUp(frame, { pointerId: 1 });

      const match = /translate\((-?[\d.]+)px/.exec(
        (screen.getAllByTestId('viewer-stage')[0] as HTMLElement).style.transform,
      );
      // At 1.25x in a 300px frame the content is 375px, so tx bottoms out at exactly
      // -75. Measuring a wider element would allow more, and measuring nothing (the
      // pre-fix behaviour, where the ref sat on an element this drag never sized)
      // would leave it at 0.
      expect(Number(match?.[1])).toBeCloseTo(-75, 5);
    } finally {
      widths.mockRestore();
      heights.mockRestore();
    }
  });

  it('renders without a result rather than collapsing the layout', () => {
    // Otherwise the panes jump sideways the first time a prediction arrives.
    render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        results={[{ key: 'r', label: 'Result', placeholder: 'Run a head to see results.' }]}
      />,
    );

    expect(stages()).toHaveLength(2);
    expect(screen.getByText('Run a head to see results.')).toBeInTheDocument();
  });

  it('keeps the placeholder outside the transform so it does not zoom', () => {
    // An overlay belongs to the image and must scale with it; a message is chrome and
    // must not. Seen in the browser: the placeholder text grew with the zoom.
    render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        results={[
          { key: 'r', label: 'Result', placeholder: <p>Run a head to see results.</p> },
        ]}
      />,
    );

    const placeholder = screen.getByText('Run a head to see results.');
    expect(stages()[1]?.contains(placeholder)).toBe(false);
    expect(screen.getAllByTestId('viewer-frame')[1]?.contains(placeholder)).toBe(true);
  });
});

describe('N-up comparison', () => {
  const paneFor = (key: string) => ({
    key,
    label: key,
    renderOverlay: () => <div data-testid={`overlay-${key}`}>{key}</div>,
  });

  it('renders one pane per result plus the original', () => {
    render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        results={[paneFor('a'), paneFor('b'), paneFor('c')]}
      />,
    );

    expect(stages()).toHaveLength(4);
    expect(screen.getByText('Original')).toBeInTheDocument();
    for (const key of ['a', 'b', 'c']) {
      expect(screen.getByTestId(`overlay-${key}`)).toBeInTheDocument();
    }
  });

  it('keeps every pane on the one transform', () => {
    // The whole reason comparison reuses this component rather than stacking N viewers:
    // four independently-zoomed panes are not a comparison.
    render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        results={[paneFor('a'), paneFor('b'), paneFor('c')]}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /zoom in/i }));

    const transforms = new Set(stages().map((stage) => stage.style.transform));
    expect(transforms.size).toBe(1);
  });

  it('tells the grid how many columns to draw', () => {
    const { container } = render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        results={[paneFor('a'), paneFor('b')]}
      />,
    );

    const panes = container.querySelector('.viewer__panes') as HTMLElement;
    expect(panes.style.getPropertyValue('--viewer-columns')).toBe('3');
  });

  it('keys panes by identity, not by position', () => {
    // Deselecting the first of three heads must not make React reuse its canvas for the
    // second head's mask — that is how one head's result ends up labelled as another's.
    const { rerender } = render(
      <SideBySideViewer
        imageUrl="/img/cat.png"
        imageAlt="cat.png"
        results={[paneFor('a'), paneFor('b')]}
      />,
    );
    rerender(
      <SideBySideViewer imageUrl="/img/cat.png" imageAlt="cat.png" results={[paneFor('b')]} />,
    );

    expect(screen.queryByTestId('overlay-a')).toBeNull();
    expect(screen.getByTestId('overlay-b')).toBeInTheDocument();
  });
});

/**
 * The player (doc 68).
 *
 * The interesting properties are the ones that make the picture and the annotation the
 * same frame, and the ones that stop someone starting a run they did not mean: the cost is
 * on screen before the click, the range is clamped to what exists, and a frame nobody has
 * analysed says so rather than showing a bare picture.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { SequenceInfo, SequenceRun } from '../api/video';
import type { SequenceRunState } from '../hooks/useSequenceRun';
import { VideoPlayer } from './VideoPlayer';

const INFO: SequenceInfo = {
  source: '/clips/rail.mp4',
  kind: 'video',
  frames: 300,
  fps: 10,
  duration: 30,
  width: 1920,
  height: 1080,
};

function runOf(over: Partial<SequenceRun> = {}): SequenceRun {
  return {
    job_id: 'j1',
    state: 'complete',
    done: 5,
    total: 5,
    unreadable: 0,
    message: '',
    start: 0,
    frames: [],
    ...over,
  };
}

function stateOf(over: Partial<SequenceRunState> = {}): SequenceRunState {
  return {
    run: null,
    error: null,
    byFrame: new Map(),
    index: 0,
    playing: false,
    start: vi.fn(),
    stop: vi.fn(),
    setIndex: vi.fn(),
    setPlaying: vi.fn(),
    clear: vi.fn(),
    ...over,
  };
}

function renderPlayer(over: Partial<SequenceRunState> = {}, props: Record<string, unknown> = {}) {
  const onRun = vi.fn();
  const state = stateOf(over);
  render(
    <VideoPlayer
      info={INFO}
      state={state}
      start={0}
      count={60}
      fps={10}
      onStartChange={vi.fn()}
      onCountChange={vi.fn()}
      onFpsChange={vi.fn()}
      onRun={onRun}
      foundationIds={['rf-detr-nano']}
      headCount={0}
      renderOverlay={() => <div data-testid="overlay" />}
      {...props}
    />,
  );
  return { onRun, state };
}

describe('before the run', () => {
  it('says what the source is', () => {
    renderPlayer();

    expect(screen.getByText(/300 frames/)).toBeInTheDocument();
    expect(screen.getByText(/10\.0 fps/)).toBeInTheDocument();
  });

  it('states the cost before the click', () => {
    // The number that changes the decision. Saying it afterwards is not saying it.
    renderPlayer(undefined, { foundationIds: ['grounded-sam'], count: 120 });

    expect(screen.getByText(/about 10 min/)).toBeInTheDocument();
    expect(screen.getByText(/an estimate/)).toBeInTheDocument();
  });

  it('quotes the clamped range, not the typed one', () => {
    // Asking for 500 from frame 250 of a 300-frame video runs 50. Quoting 500 would
    // over-state the wait by ten times.
    renderPlayer(undefined, { start: 250, count: 500 });

    expect(screen.getByRole('button', { name: /Analyse 50 frames/ })).toBeInTheDocument();
  });

  it('refuses to start with nothing selected', () => {
    // An empty run finishes instantly and reports success over nothing.
    renderPlayer(undefined, { foundationIds: [], headCount: 0 });

    expect(screen.getByRole('button', { name: /Analyse/ })).toBeDisabled();
    expect(screen.getByText(/Pick at least one head/)).toBeInTheDocument();
  });

  it('starts the run when asked', async () => {
    const user = userEvent.setup();
    const { onRun } = renderPlayer();

    await user.click(screen.getByRole('button', { name: /Analyse/ }));

    expect(onRun).toHaveBeenCalled();
  });

  it('shows no player until there is a run', () => {
    renderPlayer();

    expect(screen.queryByRole('slider', { name: 'Frame' })).not.toBeInTheDocument();
  });
});

describe('while it runs', () => {
  it('reports progress', () => {
    renderPlayer({ run: runOf({ state: 'running', done: 12, total: 60 }) });

    expect(screen.getByRole('status')).toHaveTextContent('Analysed 12 of 60 frames');
  });

  it('offers a stop', () => {
    renderPlayer({ run: runOf({ state: 'running' }) });

    expect(screen.getByRole('button', { name: 'Stop' })).toBeInTheDocument();
  });

  it('locks the range while it is running', () => {
    // Changing the range mid-run would describe a run that is not happening.
    renderPlayer({ run: runOf({ state: 'running' }) });

    expect(screen.getByLabelText(/Start at frame/)).toBeDisabled();
    expect(screen.getByLabelText(/How many frames/)).toBeDisabled();
  });

  it('leaves the play rate adjustable', () => {
    // It drives a timer in the browser, not the run — locking it would be arbitrary.
    renderPlayer({ run: runOf({ state: 'running' }) });

    expect(screen.getByLabelText(/Play at/)).not.toBeDisabled();
  });
});

describe('watching it', () => {
  const analysed = new Map([[0, []], [1, []]]);

  it('shows the frame at the run\'s own offset', () => {
    // The player counts from 0; the source counts from `run.start`. Confusing the two puts
    // frame 0's picture under frame 200's boxes.
    renderPlayer({ run: runOf({ start: 200 }), index: 3, byFrame: analysed });

    expect(screen.getByAltText('Frame 203')).toBeInTheDocument();
  });

  it('draws the overlay over the frame', () => {
    renderPlayer({ run: runOf(), index: 0, byFrame: analysed });

    expect(screen.getByTestId('overlay')).toBeInTheDocument();
  });

  it('says when a frame was never analysed', () => {
    // Otherwise a bare frame is indistinguishable from one where nothing was found.
    renderPlayer({ run: runOf({ total: 5 }), index: 4, byFrame: analysed });

    expect(screen.getByText(/not analysed/)).toBeInTheDocument();
  });

  it('says nothing of the sort for a frame that was', () => {
    renderPlayer({ run: runOf(), index: 1, byFrame: analysed });

    expect(screen.queryByText(/not analysed/)).not.toBeInTheDocument();
  });

  it('scrubbing pauses, because it is a deliberate move away from where it was', () => {
    // `fireEvent.change`, not a click: a click on a range input moves nothing in jsdom, so
    // the handler never runs and the test would pass by never exercising it.
    const { state } = renderPlayer({
      run: runOf(),
      playing: true,
      byFrame: analysed,
    });

    fireEvent.change(screen.getByRole('slider', { name: 'Frame' }), {
      target: { value: '3' },
    });

    expect(state.setPlaying).toHaveBeenCalledWith(false);
    expect(state.setIndex).toHaveBeenCalledWith(3);
  });

  it('cannot play before anything has been analysed', () => {
    renderPlayer({ run: runOf({ state: 'running', done: 0 }), byFrame: new Map() });

    expect(screen.getByRole('button', { name: 'Play' })).toBeDisabled();
  });

  it('reports frames that could not be read', () => {
    // A run that read almost nothing must not pass for one that found almost nothing.
    renderPlayer({ run: runOf({ unreadable: 3 }), byFrame: analysed });

    expect(screen.getByRole('status')).toHaveTextContent('3 could not be read');
  });
});

describe('when it fails', () => {
  it('shows the reason', () => {
    renderPlayer({ error: 'Backend is not running.' });

    expect(screen.getByRole('alert')).toHaveTextContent('Backend is not running.');
  });
});

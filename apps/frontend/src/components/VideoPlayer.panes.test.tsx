/**
 * One pane per model, side by side (2026-10-21, Jan: "all videos are on top of each other,
 * I wanted them side by side for comparison"). The same frame in each pane, each pane's
 * overlay given its own model's key, and the panes found from the run's predictions.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { Prediction } from '../api/inference';
import type { SequenceInfo } from '../api/video';
import type { SequenceRunState } from '../hooks/useSequenceRun';
import { modelPanes } from './SequencePanel';
import { VideoPlayer } from './VideoPlayer';

const INFO: SequenceInfo = {
  source: '/clips/rail.mp4', kind: 'video', frames: 300, fps: 10, duration: 30, width: 1920, height: 1080,
};

const prediction = (id: string, name: string): Prediction => ({ instance_id: id, head_name: name }) as unknown as Prediction;

function renderWith(panes: readonly { key: string; label: string }[] | undefined) {
  const renderOverlay = vi.fn((_index: number, _rendered: unknown, key: string) => <div data-testid={`overlay-${key}`} />);
  const state: SequenceRunState = {
    run: { job_id: 'j1', state: 'complete', done: 5, total: 5, unreadable: 0, message: '', start: 0, frames: [] },
    error: null, byFrame: new Map([[0, []]]), index: 0, playing: false,
    start: vi.fn(), stop: vi.fn(), setIndex: vi.fn(), setPlaying: vi.fn(), clear: vi.fn(),
  };
  render(
    <VideoPlayer info={INFO} state={state} start={0} count={60} fps={10} onStartChange={vi.fn()} onCountChange={vi.fn()}
      onFpsChange={vi.fn()} foundationIds={[]} headCount={2} renderOverlay={renderOverlay} {...(panes ? { panes } : {})} />,
  );
  return renderOverlay;
}

describe('side-by-side panes', () => {
  it('shows one labelled frame per model, each overlay with its own model', () => {
    renderWith([{ key: 'rf', label: 'RF-DETR' }, { key: 'head', label: 'Fire head' }]);
    expect(screen.getAllByRole('img')).toHaveLength(2);
    expect(screen.getByText('RF-DETR')).toBeInTheDocument();
    expect(screen.getByText('Fire head')).toBeInTheDocument();
    expect(screen.getByTestId('overlay-rf')).toBeInTheDocument();
    expect(screen.getByTestId('overlay-head')).toBeInTheDocument();
  });

  it('keeps one full-width frame for a single model, overlaying everything', () => {
    renderWith([{ key: 'rf', label: 'RF-DETR' }]);
    expect(screen.getAllByRole('img')).toHaveLength(1);
    expect(screen.queryByText('RF-DETR')).not.toBeInTheDocument();
    expect(screen.getByTestId('overlay-')).toBeInTheDocument();
  });
});

describe('modelPanes', () => {
  it('lists each model once, in the order it first answers', () => {
    const byFrame = new Map([
      [0, [prediction('rf', 'RF-DETR')]],
      [1, [prediction('head', 'Fire head'), prediction('rf', 'RF-DETR')]],
    ]);
    expect(modelPanes(byFrame)).toEqual([
      { key: 'rf', label: 'RF-DETR' },
      { key: 'head', label: 'Fire head' },
    ]);
  });
});

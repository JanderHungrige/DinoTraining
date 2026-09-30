/** The Inference Viewer's panels read German inside a German provider (doc 112). */

import { screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { FoundationInfo } from '../api/foundation';
import { NO_TILING } from '../api/inference';
import type { SequenceInfo } from '../api/video';
import { HeadRunPanel } from '../components/HeadRunPanel';
import { VideoPlayer } from '../components/VideoPlayer';
import type { HeadRunState } from '../hooks/useHeadRun';
import type { SequenceRunState } from '../hooks/useSequenceRun';
import { renderInGerman } from './testing';

const FOUNDATION = {
  id: 'rf-detr-nano',
  title: 'RF-DETR (nano)',
  description: 'General object detection.',
  task: 'detection',
  render_hint: 'boxes',
  installed: true,
  takes_concept: false,
  licence: 'Apache-2.0',
  non_commercial: true,
} as FoundationInfo;

function runState(): HeadRunState {
  return {
    heads: [],
    selected: [],
    foundations: [FOUNDATION],
    selectedFoundations: ['rf-detr-nano'],
    toggleFoundation: vi.fn(),
    tiles: NO_TILING,
    setTiles: vi.fn(),
    trainedWidth: null,
    concept: '',
    setConcept: vi.fn(),
    datasetFilter: null,
    setDatasetFilter: vi.fn(),
    trainedOn: [],
    backboneId: null,
    taskFilter: null,
    selectedTask: null,
    running: false,
    result: null,
    error: null,
    loadingHeads: false,
    toggle: vi.fn(),
    setTaskFilter: vi.fn(),
    clear: vi.fn(),
    run: vi.fn(),
    isIncompatible: () => false,
  };
}

const INFO: SequenceInfo = {
  source: '/clips/rail.mp4',
  kind: 'video',
  frames: 300,
  fps: 10,
  duration: 30,
  width: 1920,
  height: 1080,
};

const PLAYBACK: SequenceRunState = {
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
};

afterEach(() => localStorage.clear());

describe('the Inference Viewer in German', () => {
  it('names the model groups and the run button in German', () => {
    renderInGerman(<HeadRunPanel state={runState()} onRun={vi.fn()} />);

    expect(screen.getByRole('group', { name: 'Basismodelle' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '1 Modell ausführen' })).toBeEnabled();
    expect(screen.getByText(/nicht kommerziell/)).toBeInTheDocument();
  });

  it('labels the player range and its estimate in German', () => {
    renderInGerman(
      <VideoPlayer
        info={INFO}
        state={PLAYBACK}
        start={0}
        count={50}
        fps={10}
        onStartChange={vi.fn()}
        onCountChange={vi.fn()}
        onFpsChange={vi.fn()}
        onRun={vi.fn()}
        foundationIds={['rf-detr-nano']}
        headCount={0}
        renderOverlay={() => null}
      />,
    );

    expect(screen.getByLabelText('Wie viele Einzelbilder')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '50 Einzelbilder analysieren' })).toBeInTheDocument();
    expect(screen.getByText(/davon zu analysieren dauert etwa/)).toBeInTheDocument();
  });
});

/**
 * A head reads the same in every tab (doc 12's contract, made literal in Wave 5).
 *
 * Wave 5 deliberately kept **two controls**: comparison genuinely needs multi-select, and
 * annotation genuinely needs one head. What it refused to keep was two *descriptions* —
 * the same template was written out byte for byte in both components, so one edit would
 * have made the Inference Viewer and the Studio disagree about the same head with nothing
 * failing.
 *
 * This file is the guard. It renders both controls over the same head and asserts they
 * say the same thing, rather than asserting each against a hardcoded string — which would
 * pass happily if both drifted together but is silent when only one moves.
 */

import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { describeHead, type HeadInstanceInfo } from '../api/headInstances';
import { ExpertHeadPicker } from './ExpertHeadPicker';
import { HeadRunPanel } from './HeadRunPanel';
import type { HeadRunState } from '../hooks/useHeadRun';

const HEAD: HeadInstanceInfo = {
  id: 'h1',
  name: 'Thermal spotter',
  summary: 'Object detection · 2 classes · trained on 1 dataset · map 0.403',
  kind: 'trained-here',
  head_type_id: 'dense-detector',
  task: 'detection',
  render_hint: 'boxes',
  backbone_id: 'dinov2-small',
  backbone_family: 'dinov2',
  embed_dim: 384,
  num_classes: 2,
  class_names: ['dog', 'person'],
  dataset_ids: ['d1'],
  metrics: {},
  primary_metric: null,
  primary_metric_value: null,
  epochs_trained: 5,
  best_epoch: 4,
  source_repo: null,
  created_at: '2026-08-20T00:00:00+00:00',
};

function runState(): HeadRunState {
  return {
    heads: [HEAD],
    selected: [],
    foundations: [],
    selectedFoundations: [],
    toggleFoundation: vi.fn(),
    running: false,
    loadingHeads: false,
    backboneId: 'dinov2-small',
    taskFilter: null,
    selectedTask: null,
    result: null,
    error: null,
    toggle: vi.fn(),
    clear: vi.fn(),
    setTaskFilter: vi.fn(),
    run: vi.fn(),
    isIncompatible: () => false,
  } as unknown as HeadRunState;
}

describe('one head, two controls', () => {
  it('describes the head identically in the comparison panel and the picker', () => {
    const panel = render(<HeadRunPanel state={runState()} onRun={vi.fn()} />);
    const fromPanel = within(panel.container).getByText(describeHead(HEAD)).textContent;
    panel.unmount();

    const picker = render(
      <ExpertHeadPicker
        heads={[HEAD]}
        backboneId="dinov2-small"
        selectedId=""
        onSelect={vi.fn()}
      />,
    );
    const fromPicker = within(picker.container).getByText(describeHead(HEAD)).textContent;

    expect(fromPicker).toBe(fromPanel);
  });

  it('names the head from `name`, never from a filename', () => {
    render(
      <ExpertHeadPicker
        heads={[HEAD]}
        backboneId="dinov2-small"
        selectedId=""
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getByText('Thermal spotter')).toBeInTheDocument();
    // The contract's real target: a checkpoint path must never reach a label.
    expect(screen.queryByText(/\.safetensors|\.pth|\//)).not.toBeInTheDocument();
  });

  it('builds the description from `summary` as the backend composed it', () => {
    // Not reassembled here from task/num_classes — that would be a second implementation
    // of a sentence the backend already owns, free to drift from it.
    expect(describeHead(HEAD)).toContain(HEAD.summary);
  });
});

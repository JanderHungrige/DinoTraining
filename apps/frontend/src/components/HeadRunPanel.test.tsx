/**
 * Same-task comparison is the head list filtered — not a mode.
 *
 * So these tests are about the *list*: what it offers, how it names heads, and what it
 * refuses to offer. The N-up rendering that follows is tested in SideBySideViewer.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { FoundationInfo } from '../api/foundation';
import type { HeadInstanceInfo } from '../api/headInstances';
import { NO_TILING } from '../api/inference';
import type { HeadRunState } from '../hooks/useHeadRun';
import { HeadRunPanel } from './HeadRunPanel';

function head(overrides: Partial<HeadInstanceInfo> = {}): HeadInstanceInfo {
  return {
    id: 'h1',
    name: 'A segmenter',
    summary: 'Segmentation · 150 classes · pretrained default (facebookresearch/dinov2)',
    kind: 'pretrained-default',
    head_type_id: 'linear-segmenter',
    task: 'segmentation',
    render_hint: 'masks',
    backbone_id: 'dinov2-small',
    backbone_family: 'dinov2',
    embed_dim: 384,
    num_classes: 150,
    class_names: [],
    dataset_ids: [],
    metrics: {},
    primary_metric: null,
    primary_metric_value: null,
    epochs_trained: 0,
    best_epoch: null,
    source_repo: 'facebookresearch/dinov2',
    created_at: '2026-08-18T00:00:00Z',
    ...overrides,
  };
}

function state(overrides: Partial<HeadRunState> = {}): HeadRunState {
  return {
    heads: [],
    selected: [],
    foundations: [],
    selectedFoundations: [],
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
    ...overrides,
  };
}

function foundation(overrides: Partial<FoundationInfo> = {}): FoundationInfo {
  return {
    id: 'rf-detr-nano',
    title: 'RF-DETR (nano)',
    description: 'General object detection.',
    task: 'detection',
    render_hint: 'boxes',
    installed: true,
    takes_concept: false,
    licence: 'Apache-2.0',
    non_commercial: false,
    ...overrides,
  } as FoundationInfo;
}

describe('with no heads installed', () => {
  /**
   * Reported as "in the inference tab no model shows up until you install a pretrained
   * head, even though a foundation model is already installed".
   *
   * The panel returned early on `heads.length === 0`, before the Foundation models group
   * rendered at all. So a fresh install — which the starter set fills with RF-DETR,
   * Grounded SAM and Depth Anything, none of which needs a head — was told to go and
   * install a head, and installing one made four models appear at once.
   */
  it('offers an installed foundation model with no head anywhere', () => {
    render(
      <HeadRunPanel
        state={state({ heads: [], foundations: [foundation()] })}
        onRun={vi.fn()}
      />,
    );

    expect(screen.getByRole('checkbox', { name: /RF-DETR/ })).toBeInTheDocument();
    expect(screen.queryByText(/Nothing to run yet/)).not.toBeInTheDocument();
  });

  it('can select and run one', () => {
    // The empty state was not only a wording problem: nothing was reachable to tick.
    const toggleFoundation = vi.fn();
    render(
      <HeadRunPanel
        state={state({ heads: [], foundations: [foundation()], toggleFoundation })}
        onRun={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole('checkbox', { name: /RF-DETR/ }));

    expect(toggleFoundation).toHaveBeenCalledWith('rf-detr-nano');
  });

  it('hides the Heads group rather than showing an empty one', () => {
    // An empty bordered "Heads" box beside a populated list reads as a failed load.
    render(
      <HeadRunPanel
        state={state({ heads: [], foundations: [foundation()] })}
        onRun={vi.fn()}
      />,
    );

    expect(screen.queryByRole('group', { name: 'Heads' })).not.toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Foundation models' })).toBeInTheDocument();
  });

  it('hides the head filters, which would have nothing to filter', () => {
    render(
      <HeadRunPanel
        state={state({ heads: [], foundations: [foundation()] })}
        onRun={vi.fn()}
      />,
    );

    expect(screen.queryByLabelText('Task')).not.toBeInTheDocument();
  });

  it('still says so when there is genuinely nothing installed', () => {
    render(<HeadRunPanel state={state({ heads: [], foundations: [] })} onRun={vi.fn()} />);

    expect(screen.getByRole('status')).toHaveTextContent(/Nothing to run yet/);
  });

  it('asks for a concept when a concept model is the only thing selected', () => {
    // Grounded SAM with no head installed is the exact fresh-install case, and a concept
    // model with no concept returns an all-background mask that means nothing was asked.
    render(
      <HeadRunPanel
        state={state({
          heads: [],
          foundations: [
            foundation({ id: 'grounded-sam', title: 'Grounded SAM', takes_concept: true }),
          ],
          selectedFoundations: ['grounded-sam'],
        })}
        onRun={vi.fn()}
      />,
    );

    expect(screen.getByLabelText(/What to find/)).toBeInTheDocument();
  });
});

const SEGMENTERS = [
  head({ id: 'a', name: 'ADE20k segmenter' }),
  head({ id: 'b', name: 'My segmenter', kind: 'trained-here' }),
];
const CLASSIFIER = head({
  id: 'c',
  name: 'ImageNet classifier',
  task: 'classification',
  head_type_id: 'linear-classifier',
  summary: 'Classification · 1000 classes · pretrained default',
});

describe('HeadRunPanel', () => {
  it('presents heads by summary, never by a filename', () => {
    // Doc 12's cross-tab contract. Wave 2 shipped a bug from breaking it.
    render(<HeadRunPanel state={state({ heads: [SEGMENTERS[0] as HeadInstanceInfo] })} onRun={vi.fn()} />);

    expect(screen.getByText(/150 classes/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/\.safetensors|\.pth|\.bin/);
  });

  it('offers only the tasks the installed heads actually cover', () => {
    render(
      <HeadRunPanel state={state({ heads: [...SEGMENTERS, CLASSIFIER] })} onRun={vi.fn()} />,
    );

    const options = [...screen.getByLabelText('Task').querySelectorAll('option')].map(
      (option) => option.textContent,
    );
    expect(options).toEqual(['All tasks', 'classification', 'segmentation']);
  });

  it('narrows the list to one task', () => {
    render(
      <HeadRunPanel
        state={state({ heads: [...SEGMENTERS, CLASSIFIER], taskFilter: 'segmentation' })}
        onRun={vi.fn()}
      />,
    );

    expect(screen.getByText('ADE20k segmenter')).toBeInTheDocument();
    expect(screen.getByText('My segmenter')).toBeInTheDocument();
    expect(screen.queryByText('ImageNet classifier')).toBeNull();
  });

  it('reports when a selection is a same-task comparison', () => {
    render(
      <HeadRunPanel
        state={state({
          heads: SEGMENTERS,
          selected: ['a', 'b'],
          selectedTask: 'segmentation',
        })}
        onRun={vi.fn()}
      />,
    );

    expect(screen.getByText(/Comparing 2 heads on segmentation/)).toBeInTheDocument();
  });

  it('says nothing about comparison for a single head', () => {
    render(
      <HeadRunPanel
        state={state({ heads: SEGMENTERS, selected: ['a'], selectedTask: 'segmentation' })}
        onRun={vi.fn()}
      />,
    );

    expect(screen.queryByText(/Comparing/)).toBeNull();
  });

  it('disables a head registered for a different backbone, and says why', () => {
    const other = head({ id: 'x', name: 'Other backbone head', backbone_id: 'dinov2-base' });
    render(
      <HeadRunPanel
        state={state({
          heads: [SEGMENTERS[0] as HeadInstanceInfo, other],
          selected: ['a'],
          backboneId: 'dinov2-small',
          isIncompatible: (candidate) => candidate.backbone_id !== 'dinov2-small',
        })}
        onRun={vi.fn()}
      />,
    );

    const label = screen.getByText('Other backbone head').closest('label') as HTMLElement;
    expect(label.querySelector('input')).toBeDisabled();
    expect(label.title).toMatch(/dinov2-base/);
  });

  it('reports the backbone passes the run actually cost', () => {
    render(
      <HeadRunPanel
        state={state({
          heads: SEGMENTERS,
          selected: ['a', 'b'],
          result: { predictions: [], passes: 1, elapsed_ms: 412.7 },
        })}
        onRun={vi.fn()}
      />,
    );

    // Two heads, one pass — the saving doc 18 exists for, made visible to the user.
    expect(screen.getByText(/1 backbone pass · 413 ms/)).toBeInTheDocument();
  });

  it('cannot run with nothing selected', () => {
    render(<HeadRunPanel state={state({ heads: SEGMENTERS })} onRun={vi.fn()} />);

    expect(screen.getByRole('button', { name: /^Run/ })).toBeDisabled();
  });

  it('points at where heads come from when there are none', () => {
    render(<HeadRunPanel state={state()} onRun={vi.fn()} />);

    expect(screen.getByText(/Admin tab/)).toBeInTheDocument();
  });

  it('runs the selection', () => {
    const onRun = vi.fn();
    render(
      <HeadRunPanel state={state({ heads: SEGMENTERS, selected: ['a'] })} onRun={onRun} />,
    );

    fireEvent.click(screen.getByRole('button', { name: /^Run/ }));

    expect(onRun).toHaveBeenCalled();
  });
});

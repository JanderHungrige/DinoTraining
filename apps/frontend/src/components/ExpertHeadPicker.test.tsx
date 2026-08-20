import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { HeadInstanceInfo } from '../api/headInstances';
import { ExpertHeadPicker } from './ExpertHeadPicker';

function head(overrides: Partial<HeadInstanceInfo> = {}): HeadInstanceInfo {
  return {
    id: 'h1',
    name: 'Bolt finder',
    summary: 'Object detection · 2 classes · trained on 1 dataset',
    kind: 'trained-here',
    head_type_id: 'dense-detector',
    task: 'detection',
    render_hint: 'boxes',
    backbone_id: 'dinov2-small',
    backbone_family: 'dinov2',
    embed_dim: 384,
    num_classes: 2,
    class_names: ['bolt', 'nut'],
    dataset_ids: ['d1'],
    metrics: {},
    primary_metric: null,
    primary_metric_value: null,
    epochs_trained: 5,
    best_epoch: 4,
    source_repo: null,
    created_at: '2026-08-19T00:00:00+00:00',
    ...overrides,
  };
}

function renderPicker(
  heads: readonly HeadInstanceInfo[],
  props: Partial<Parameters<typeof ExpertHeadPicker>[0]> = {},
) {
  const onSelect = vi.fn();
  render(
    <ExpertHeadPicker
      heads={heads}
      backboneId="dinov2-small"
      selectedId=""
      onSelect={onSelect}
      {...props}
    />,
  );
  return { onSelect };
}

describe('ExpertHeadPicker', () => {
  it('offers a detection head', () => {
    renderPicker([head()]);
    expect(screen.getByRole('radio', { name: /Bolt finder/ })).toBeInTheDocument();
  });

  it('filters on render_hint, not on task', () => {
    // A head whose task says "detection" but which renders masks must not be offered:
    // the annotator refuses it at run time, and the picker should never have shown it.
    renderPicker([head({ id: 'h2', name: 'Mislabelled', render_hint: 'masks' })]);
    expect(screen.queryByRole('radio', { name: /Mislabelled/ })).not.toBeInTheDocument();
  });

  it('excludes classification, segmentation and depth heads', () => {
    renderPicker([
      head({ id: 'a', name: 'Classifier', render_hint: 'labels' }),
      head({ id: 'b', name: 'Segmenter', render_hint: 'masks' }),
      head({ id: 'c', name: 'Depth', render_hint: 'depth-map' }),
    ]);
    expect(screen.queryAllByRole('radio')).toHaveLength(0);
  });

  it('excludes a detection head trained on another backbone', () => {
    renderPicker([head({ backbone_id: 'dinov2-base' })]);
    expect(screen.queryByRole('radio')).not.toBeInTheDocument();
  });

  it('says why when nothing can annotate, and points at the Head Trainer', () => {
    renderPicker([head({ render_hint: 'masks' })]);
    expect(screen.getByRole('status')).toHaveTextContent(/Head Trainer/);
  });

  it('distinguishes "wrong backbone" from "nothing can annotate"', () => {
    // Two different fixes; one message for both would send the user to the wrong place.
    renderPicker([head({ backbone_id: 'dinov2-base' })]);
    const message = screen.getByRole('status').textContent ?? '';
    expect(message).toMatch(/dinov2-small/);
    expect(message).not.toMatch(/Head Trainer/);
  });

  it('renders the provenance summary, never a filename', () => {
    renderPicker([head()]);
    expect(screen.getByText(/Trained here · Object detection/)).toBeInTheDocument();
    expect(screen.queryByText(/\.safetensors/)).not.toBeInTheDocument();
  });

  it('reports the chosen head', async () => {
    const user = userEvent.setup();
    const { onSelect } = renderPicker([head(), head({ id: 'h2', name: 'Nut finder' })]);

    await user.click(screen.getByRole('radio', { name: /Nut finder/ }));
    expect(onSelect).toHaveBeenCalledWith('h2');
  });

  it('is single-select — picking one head cannot select two', async () => {
    const user = userEvent.setup();
    renderPicker([head(), head({ id: 'h2', name: 'Nut finder' })], { selectedId: 'h1' });

    await user.click(screen.getByRole('radio', { name: /Nut finder/ }));
    const checked = screen.getAllByRole('radio').filter((r) => (r as HTMLInputElement).checked);
    expect(checked.length).toBeLessThanOrEqual(1);
  });

  it('shows a loading state rather than an empty one while heads arrive', () => {
    renderPicker([], { loading: true });
    expect(screen.getByRole('status')).toHaveTextContent(/Loading heads/);
  });

  describe('sharing it between two tabs (doc 32)', () => {
    it('defaults to the Generator wording it shipped with', () => {
      renderPicker([head()]);
      expect(screen.getByRole('group', { name: 'Expert head' })).toBeInTheDocument();
    });

    it("takes the calling tab's legend", () => {
      renderPicker([head()], { legend: 'Annotate with' });
      expect(screen.getByRole('group', { name: 'Annotate with' })).toBeInTheDocument();
    });

    it('takes a radio group name, so two pickers on one page cannot fight', () => {
      // Radios sharing a `name` form one group: selecting in the second silently clears
      // the first. Nothing renders two today; this is what makes it safe when something does.
      renderPicker([head()], { groupName: 'studio-head' });
      expect(screen.getByRole('radio')).toHaveAttribute('name', 'studio-head');
    });

    it('names the radio group `expert-head` when the caller says nothing', () => {
      renderPicker([head()]);
      expect(screen.getByRole('radio')).toHaveAttribute('name', 'expert-head');
    });

    it('still refuses a head whose render_hint is not boxes, whatever the legend says', () => {
      // The rule that confines the Studio to box heads. `task` is deliberately left as
      // `detection` so a filter written against the wrong field would pass this.
      renderPicker([head({ render_hint: 'masks' })], { legend: 'Annotate with' });
      expect(screen.queryByRole('radio')).not.toBeInTheDocument();
      expect(screen.getByRole('status')).toHaveTextContent(/No installed head can propose boxes/);
    });
  });
});

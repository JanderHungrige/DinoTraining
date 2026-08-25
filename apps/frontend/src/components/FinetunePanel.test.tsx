/**
 * The fine-tuning panel (doc 44 UI).
 *
 * Three things carry real risk and get the attention: that only a *base* detector can be
 * fine-tuned, that the frozen/trainable split is shown rather than claimed, and that the
 * form cannot start a run it has not been given enough to describe.
 */

import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { DatasetInfo } from '../api/datasets';
import type { FinetuneJob, FoundationInfo } from '../api/foundation';
import { FinetunePanel } from './FinetunePanel';

const BASE: FoundationInfo = {
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

/** A model the user already fine-tuned: installed, but not a base to start from. */
const TUNED: FoundationInfo = {
  ...BASE,
  id: 'abc123',
  title: 'Thermal RF-DETR',
  description: 'fine-tuned from rf-detr-nano · 2 classes · map 0.800',
  approx_size_mb: 0,
  takes_concept: false,
};

const DEPTH: FoundationInfo = {
  ...BASE,
  id: 'depth-anything-v2-small',
  title: 'Depth Anything V2',
  render_hint: 'depth-map',
  task: 'depth',
};

const DATASET = {
  id: 'd1',
  name: 'Thermal',
  counts: { images: 203 },
} as unknown as DatasetInfo;

function job(overrides: Partial<FinetuneJob> = {}): FinetuneJob {
  return {
    job_id: 'j1',
    state: 'running',
    epoch: 2,
    total_epochs: 6,
    best_metric: 0.77,
    class_names: ['dog', 'person'],
    frozen_parameters: 23_266_048,
    trainable_parameters: 6_881_028,
    message: '',
    instance_id: null,
    history: [{ epoch: 2, train_loss: 5.05, metrics: { map: 0.77 } }],
    ...overrides,
  };
}

function renderPanel(props: Partial<Parameters<typeof FinetunePanel>[0]> = {}) {
  const onStart = vi.fn();
  const onCancel = vi.fn();
  render(
    <FinetunePanel
      datasets={[DATASET]}
      foundations={[BASE]}
      job={null}
      starting={false}
      running={false}
      error={null}
      onStart={onStart}
      onCancel={onCancel}
      {...props}
    />,
  );
  return { onStart, onCancel, user: userEvent.setup() };
}

describe('what can be fine-tuned', () => {
  it('offers an installed base detector', () => {
    renderPanel();
    expect(screen.getByRole('radio', { name: /RF-DETR/ })).toBeInTheDocument();
  });

  it('does not offer a model that is itself a fine-tune', () => {
    // Training a fine-tune again compounds its drift from the COCO weights it started at,
    // and the user almost certainly means "start over from the base".
    renderPanel({ foundations: [BASE, TUNED] });
    expect(screen.queryByRole('radio', { name: /Thermal RF-DETR/ })).not.toBeInTheDocument();
  });

  it('does not offer a depth model', () => {
    // `render_hint`, not `task` — the same authoritative field the rest of the app uses.
    renderPanel({ foundations: [BASE, DEPTH] });
    expect(screen.queryByRole('radio', { name: /Depth Anything/ })).not.toBeInTheDocument();
  });

  it('says where to get one when nothing is installed', () => {
    renderPanel({ foundations: [] });
    expect(screen.getByRole('status')).toHaveTextContent(/Admin \/ Models/);
  });
});

describe('starting a run', () => {
  it('will not start without a name', async () => {
    const { user } = renderPanel();
    await user.click(screen.getByRole('checkbox', { name: /Thermal/ }));
    expect(screen.getByRole('button', { name: 'Fine-tune' })).toBeDisabled();
  });

  it('will not start without a dataset', async () => {
    const { user } = renderPanel();
    await user.type(screen.getByLabelText('Name'), 'My detector');
    expect(screen.getByRole('button', { name: 'Fine-tune' })).toBeDisabled();
  });

  it('passes the base, the datasets and the name', async () => {
    const { onStart, user } = renderPanel();

    await user.type(screen.getByLabelText('Name'), 'My detector');
    await user.click(screen.getByRole('checkbox', { name: /Thermal/ }));
    await user.click(screen.getByRole('button', { name: 'Fine-tune' }));

    expect(onStart).toHaveBeenCalledWith(
      expect.objectContaining({
        foundationId: 'rf-detr-nano',
        datasetIds: ['d1'],
        name: 'My detector',
      }),
    );
  });

  it('defaults to a fine-tuning epoch count, not a head-training one', async () => {
    const { onStart, user } = renderPanel();
    await user.type(screen.getByLabelText('Name'), 'x');
    await user.click(screen.getByRole('checkbox', { name: /Thermal/ }));
    await user.click(screen.getByRole('button', { name: 'Fine-tune' }));

    expect(onStart.mock.calls[0]?.[0].epochs).toBeLessThanOrEqual(10);
  });

  it('warns that this is minutes, not seconds', () => {
    // Head training next to it finishes in seconds. Someone who expects the same and
    // gets six minutes concludes it has hung.
    renderPanel();
    expect(screen.getByText(/minutes/)).toBeInTheDocument();
  });
});

describe('while it runs', () => {
  it('shows the frozen and trainable split rather than claiming it', () => {
    // The whole feature rests on the backbone actually being frozen, and a freeze that
    // silently did nothing looks exactly like a slow success.
    renderPanel({ job: job(), running: true });
    expect(screen.getByText(/23\.3M frozen/)).toBeInTheDocument();
    expect(screen.getByText(/6\.9M training/)).toBeInTheDocument();
  });

  it('reports progress against the epoch budget', () => {
    renderPanel({ job: job(), running: true });
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '33');
  });

  it('offers a stop that keeps the best model', async () => {
    // The runner saves on every improvement, so stopping is not throwing the run away —
    // the button says so.
    const { onCancel, user } = renderPanel({ job: job(), running: true });
    await user.click(screen.getByRole('button', { name: /Stop, keep best/ }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('locks the form so a running config cannot drift from the job', async () => {
    renderPanel({ job: job(), running: true });
    expect(screen.getByLabelText('Name')).toBeDisabled();
    expect(screen.getByRole('checkbox', { name: /Thermal/ })).toBeDisabled();
  });

  it('says where the result went once it is saved', () => {
    renderPanel({ job: job({ state: 'complete', instance_id: 'abc' }), running: false });
    expect(screen.getByText(/Annotation Studio/)).toBeInTheDocument();
  });
});

describe('training the backbone too (doc 55)', () => {
  it('defaults to frozen', async () => {
    // The founding rule, the fastest run, and the right choice unless placement is what
    // is wrong.
    const { onStart, user } = renderPanel();
    await user.type(screen.getByLabelText('Name'), 'x');
    await user.click(screen.getByRole('checkbox', { name: /Thermal/ }));
    await user.click(screen.getByRole('button', { name: 'Fine-tune' }));
    expect(onStart.mock.calls[0]?.[0].unfreezeBlocks).toBe(0);
  });

  it('says what frozen means rather than leaving the slider unexplained', () => {
    renderPanel();
    expect(screen.getByText(/founding rule/)).toBeInTheDocument();
  });

  it('reports the chosen block count', async () => {
    const { onStart, user } = renderPanel();
    const slider = screen.getByLabelText(/Train the backbone too/);
    fireEvent.change(slider, { target: { value: '4' } });
    await user.type(screen.getByLabelText('Name'), 'x');
    await user.click(screen.getByRole('checkbox', { name: /Thermal/ }));
    await user.click(screen.getByRole('button', { name: 'Fine-tune' }));
    expect(onStart.mock.calls[0]?.[0].unfreezeBlocks).toBe(4);
  });

  it('gives the measured trade rather than a vague promise', () => {
    // "May improve accuracy" is not a reason to spend 19% more time. Numbers are.
    renderPanel();
    const slider = screen.getByLabelText(/Train the backbone too/);
    fireEvent.change(slider, { target: { value: '4' } });
    expect(screen.getByText(/0\.781 to 0\.843/)).toBeInTheDocument();
    expect(screen.getByText(/19% more time/)).toBeInTheDocument();
  });

  it('locks while a run is going', () => {
    renderPanel({ job: job(), running: true });
    expect(screen.getByLabelText(/Train the backbone too/)).toBeDisabled();
  });
});

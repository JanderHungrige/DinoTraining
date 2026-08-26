/**
 * The starter set (doc 65).
 *
 * Reported as "there are no preinstalled models" — and there cannot be: the set is ~1.1 GB,
 * which is too much for a git clone and several times the whole installer, and the gated
 * models may not be redistributed at all. So the goal is one click rather than zero, and
 * what these tests hold is that the one click is honest: it says the size before you commit
 * to it, it downloads one at a time so the progress figures mean something, and it gets out
 * of the way once there is nothing left to do.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { DownloadJob, ModelInfo } from '../api/models';
import { StarterSetPanel, starterState } from './StarterSetPanel';

function model(id: string, over: Partial<ModelInfo> = {}): ModelInfo {
  return {
    id,
    repo_id: `org/${id}`,
    kind: 'backbone',
    family: 'dinov2',
    gated: false,
    approx_size_mb: 100,
    description: '',
    licence: 'Apache-2.0',
    licence_url: '',
    requires_access_request: false,
    non_commercial: false,
    installed: false,
    starter: true,
    ...over,
  } as ModelInfo;
}

function job(over: Partial<DownloadJob> = {}): DownloadJob {
  return {
    job_id: 'j1',
    model_id: 'a',
    state: 'downloading',
    downloaded_bytes: 0,
    total_bytes: 0,
    message: '',
    ...over,
  } as DownloadJob;
}

function renderPanel(
  models: ModelInfo[],
  jobs: Record<string, DownloadJob> = {},
) {
  const onDownload = vi.fn<(id: string) => Promise<void>>().mockResolvedValue(undefined);
  const { container } = render(
    <StarterSetPanel models={models} jobs={jobs} onDownload={onDownload} />,
  );
  return { container, onDownload, user: userEvent.setup() };
}

describe('which models it offers', () => {
  it('takes the set from the catalogue rather than deciding it here', () => {
    // `starter` is a field on the model, so the API and the UI cannot disagree about
    // what a new user needs.
    const state = starterState([
      model('dinov2-small'),
      model('dinov2-large', { starter: false }),
    ]);

    expect(state.starter.map((entry) => entry.id)).toEqual(['dinov2-small']);
  });

  it('offers only what is missing', () => {
    const state = starterState([
      model('a', { installed: true }),
      model('b', { installed: false }),
    ]);

    expect(state.missing.map((entry) => entry.id)).toEqual(['b']);
  });

  it('adds up only the missing ones', () => {
    // Counting the installed ones would quote a gigabyte for a download of two hundred
    // megabytes, which is the kind of wrong that stops someone pressing the button.
    const state = starterState([
      model('a', { installed: true, approx_size_mb: 900 }),
      model('b', { installed: false, approx_size_mb: 200 }),
    ]);

    expect(state.megabytes).toBe(200);
  });
});

describe('what it says before you commit', () => {
  it('puts the total size on the button', () => {
    // A gigabyte is a real decision on a tether or a metered link. Saying so afterwards
    // is not saying so.
    renderPanel([model('a', { approx_size_mb: 658 }), model('b', { approx_size_mb: 471 })]);

    expect(screen.getByRole('button', { name: /1\.1 GB/ })).toBeInTheDocument();
  });

  it('lists each model and its size', () => {
    renderPanel([model('grounding-dino-tiny', { approx_size_mb: 658 })]);

    expect(screen.getByText('grounding-dino-tiny')).toBeInTheDocument();
    expect(screen.getByText('658 MB')).toBeInTheDocument();
  });

  it('says nothing is bundled, because that is the question being answered', () => {
    renderPanel([model('a')]);

    expect(screen.getByText(/Nothing is bundled/)).toBeInTheDocument();
  });
});

describe('downloading', () => {
  it('downloads every missing model', async () => {
    const { onDownload, user } = renderPanel([model('a'), model('b'), model('c')]);

    await user.click(screen.getByRole('button', { name: /Download all/ }));

    await waitFor(() => expect(onDownload).toHaveBeenCalledTimes(3));
  });

  it('downloads them one at a time', async () => {
    // Five parallel HuggingFace pulls saturate the link and make every progress figure
    // lie about its own speed.
    const order: string[] = [];
    // Held in an object because TypeScript narrows a `let` assigned only inside a callback
    // to `null`, and then refuses to call it.
    const gate: { release: () => void } = { release: () => undefined };
    const onDownload = vi.fn(async (id: string) => {
      order.push(`start:${id}`);
      await new Promise<void>((resolve) => {
        gate.release = () => {
          order.push(`end:${id}`);
          resolve();
        };
      });
    });
    render(
      <StarterSetPanel models={[model('a'), model('b')]} jobs={{}} onDownload={onDownload} />,
    );

    await userEvent.setup().click(screen.getByRole('button', { name: /Download all/ }));
    await waitFor(() => expect(order).toEqual(['start:a']));

    // `b` has not started while `a` is still in flight.
    expect(onDownload).toHaveBeenCalledTimes(1);
    gate.release();
    await waitFor(() => expect(order).toEqual(['start:a', 'end:a', 'start:b']));
  });

  it('cannot be started twice', async () => {
    const { user } = renderPanel([model('a')], { a: job({ state: 'downloading' }) });

    expect(screen.getByRole('button', { name: /Downloading/ })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: /Downloading/ }));
  });

  it('treats a claimed-but-not-started download as in flight', () => {
    // `pending` means the job exists. Offering the button again would queue it twice.
    renderPanel([model('a')], { a: job({ state: 'pending' }) });

    expect(screen.getByRole('button', { name: /Downloading/ })).toBeDisabled();
  });
});

describe('progress', () => {
  it('shows a percentage once the total is known', () => {
    renderPanel([model('a')], {
      a: job({ downloaded_bytes: 50_000_000, total_bytes: 100_000_000 }),
    });

    expect(screen.getByText('50%')).toBeInTheDocument();
  });

  it('shows megabytes when the server sent no total', () => {
    // HuggingFace does not always send a content length. `0 / 0` renders as a confident
    // NaN% or a bar pinned at zero — both of which read as a stall rather than as a
    // missing number.
    renderPanel([model('a')], { a: job({ downloaded_bytes: 42_000_000, total_bytes: 0 }) });

    expect(screen.getByText('42 MB')).toBeInTheDocument();
  });

  it('says so when one failed rather than showing it as pending forever', () => {
    renderPanel([model('a')], { a: job({ state: 'failed' }) });

    expect(screen.getByText('failed')).toBeInTheDocument();
  });
});

describe('when there is nothing to do', () => {
  it('collapses to one line once everything is installed', () => {
    renderPanel([model('a', { installed: true })]);

    expect(screen.queryByRole('button')).not.toBeInTheDocument();
    expect(screen.getByText(/Ready to use/)).toBeInTheDocument();
  });

  it('renders nothing at all before the catalogue loads', () => {
    // An empty bordered panel above the catalogue reads as a failure.
    const { container } = renderPanel([]);

    expect(container).toBeEmptyDOMElement();
  });
});

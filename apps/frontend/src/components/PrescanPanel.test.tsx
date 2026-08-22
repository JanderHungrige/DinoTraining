/**
 * Skipping the empty images (doc 53).
 *
 * The escape hatch is the part that matters: the model may simply be wrong, so seeing every
 * image again must never be more than one click away, and a scan must never leave the user
 * unable to tell "found nothing" from "could not read anything".
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { PrescanJob } from '../api/prescan';
import { PrescanPanel } from './PrescanPanel';

function job(over: Partial<PrescanJob> = {}): PrescanJob {
  return {
    job_id: 'j1',
    state: 'complete',
    scanned: 400,
    total: 400,
    unreadable: 0,
    hits: [
      { path: '/a.png', boxes: 2, best_score: 0.9, labels: ['person'] },
      { path: '/b.png', boxes: 1, best_score: 0.5, labels: ['person'] },
    ],
    message: '',
    ...over,
  };
}

function renderPanel(over: Partial<Parameters<typeof PrescanPanel>[0]> = {}) {
  const handlers = { onScan: vi.fn(), onCancel: vi.fn(), onApply: vi.fn() };
  render(
    <PrescanPanel
      total={400}
      job={null}
      starting={false}
      running={false}
      error={null}
      filtered={false}
      suggestions={[]}
      {...handlers}
      {...over}
    />,
  );
  return { ...handlers, user: userEvent.setup() };
}

async function open(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole('button', { name: /Skip the empty images/ }));
}

describe('opening it', () => {
  it('is collapsed by default', () => {
    // It answers a question most sessions never ask; a panel of controls above the image
    // is a tax on the common case.
    renderPanel();
    expect(screen.queryByLabelText(/Looking for/)).not.toBeInTheDocument();
  });

  it('says what it will do, and that nothing is saved', async () => {
    const { user } = renderPanel();
    await open(user);
    expect(screen.getByText(/Nothing is saved/)).toBeInTheDocument();
  });

  it('names how many images it would scan', async () => {
    const { user } = renderPanel();
    await open(user);
    expect(screen.getByRole('button', { name: 'Scan 400 images' })).toBeInTheDocument();
  });
});

describe('starting a scan', () => {
  it('passes the labels and the threshold', async () => {
    const { onScan, user } = renderPanel();
    await open(user);
    await user.type(screen.getByLabelText(/Looking for/), 'person, bicycle');
    await user.click(screen.getByRole('button', { name: /Scan 400/ }));
    expect(onScan).toHaveBeenCalledWith(['person', 'bicycle'], 0.3);
  });

  it('treats an empty label box as "anything the model finds"', async () => {
    // Right default for a single-class head: asking the user to retype the only class it
    // knows is a question with one answer.
    const { onScan, user } = renderPanel();
    await open(user);
    await user.click(screen.getByRole('button', { name: /Scan 400/ }));
    expect(onScan).toHaveBeenCalledWith([], 0.3);
  });

  it('drops a trailing comma rather than sending a blank label', async () => {
    const { onScan, user } = renderPanel();
    await open(user);
    await user.type(screen.getByLabelText(/Looking for/), 'person,');
    await user.click(screen.getByRole('button', { name: /Scan 400/ }));
    expect(onScan).toHaveBeenCalledWith(['person'], 0.3);
  });

  it('suggests what the session is already looking for', async () => {
    const { user } = renderPanel({ suggestions: ['a cat', 'a dog'] });
    await open(user);
    expect(screen.getByLabelText(/Looking for/)).toHaveAttribute(
      'placeholder',
      'a cat, a dog',
    );
  });
});

describe('while it runs', () => {
  it('reports progress and matches so far', async () => {
    const { user } = renderPanel({ running: true, job: job({ state: 'running', scanned: 100 }) });
    await open(user);
    expect(screen.getByText(/100 of 400/)).toBeInTheDocument();
    expect(screen.getByText(/2 matches so far/)).toBeInTheDocument();
  });

  it('offers a stop that keeps what it found', async () => {
    const { onCancel, user } = renderPanel({
      running: true,
      job: job({ state: 'running' }),
    });
    await open(user);
    await user.click(screen.getByRole('button', { name: /Stop, keep what it found/ }));
    expect(onCancel).toHaveBeenCalled();
  });
});

describe('after it finishes', () => {
  it('says how many matched', async () => {
    const { user } = renderPanel({ job: job() });
    await open(user);
    expect(screen.getByRole('status')).toHaveTextContent(/2 of 400/);
  });

  it('offers the filter as a toggle, not a commitment', async () => {
    // The model may simply be wrong; checking every image must stay one click away.
    const { onApply, user } = renderPanel({ job: job() });
    await open(user);
    await user.click(screen.getByRole('checkbox'));
    expect(onApply).toHaveBeenCalledWith(true);
  });

  it('turns the filter back off', async () => {
    const { onApply, user } = renderPanel({ job: job(), filtered: true });
    await open(user);
    await user.click(screen.getByRole('checkbox'));
    expect(onApply).toHaveBeenCalledWith(false);
  });

  it('cannot filter to nothing', async () => {
    const { user } = renderPanel({ job: job({ hits: [] }) });
    await open(user);
    expect(screen.getByRole('checkbox')).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent(/nothing to show/);
  });

  it('reports images it could not read', async () => {
    // Otherwise a scan that read almost nothing passes for one that found almost nothing.
    const { user } = renderPanel({ job: job({ unreadable: 7 }) });
    await open(user);
    expect(screen.getByRole('status')).toHaveTextContent(/7.*could not be read/);
  });

  it('says when the scan failed rather than reporting zero matches', async () => {
    const { user } = renderPanel({
      job: job({ state: 'failed', hits: [], message: 'weights missing' }),
    });
    await open(user);
    expect(screen.getByRole('status')).toHaveTextContent(/weights missing/);
  });

  it('says when it was stopped early', async () => {
    const { user } = renderPanel({ job: job({ state: 'cancelled', scanned: 120 }) });
    await open(user);
    expect(screen.getByRole('status')).toHaveTextContent(/before you stopped it/);
  });
});

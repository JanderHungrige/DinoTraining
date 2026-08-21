/**
 * Choosing what proposes the boxes.
 *
 * Two things are worth testing here and the rest is form plumbing:
 *   1. the modes are **exclusive on screen** — head mode has no prompt field, and the
 *      config that comes out can only ever describe one of them;
 *   2. the head selection is **derived, not seeded** from an async fetch. Seeding
 *      `useState` from data that has not arrived is this project's most-repeated bug: the
 *      state stays '' while the list renders anyway, so the form looks filled in and the
 *      submit button never enables. The test that catches it has to render empty first and
 *      only then supply data — which is the sequence a real load produces.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { HeadInstanceInfo } from '../api/headInstances';
import { SessionSetup } from './SessionSetup';

const fetchMock = vi.fn<typeof fetch>();

function head(overrides: Partial<HeadInstanceInfo> = {}): HeadInstanceInfo {
  return {
    id: 'h1',
    name: 'Thermal spotter',
    summary: 'Object detection · 2 classes · trained on 1 dataset',
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
    ...overrides,
  };
}

function json(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'Content-Type': 'application/json' },
  });
}

const CREATED = {
  id: 'ds-new',
  name: 'Thermal',
  created_at: '2026-08-20T00:00:00+00:00',
  prompt: null,
  copy_images: false,
  counts: { images: 0, boxes: 0, masks: 0, positive: 0, negative: 0, unclear: 0 },
};

function routes(heads: readonly HeadInstanceInfo[]): void {
  fetchMock.mockImplementation((input: unknown, init?: RequestInit) => {
    const url = String(input);
    if (url.includes('/heads')) return Promise.resolve(json({ heads }));
    // Route by method, not just path: submitting creates the dataset before it starts,
    // and a list-shaped body there fails validation and swallows the whole submit.
    if (url.includes('/datasets') && init?.method === 'POST') {
      return Promise.resolve(json(CREATED));
    }
    if (url.includes('/datasets')) return Promise.resolve(json({ datasets: [] }));
    return Promise.resolve(json({}));
  });
}

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

async function setup(heads: readonly HeadInstanceInfo[] = [head()]) {
  routes(heads);
  const onStart = vi.fn();
  render(<SessionSetup onStart={onStart} />);
  await waitFor(() => expect(fetchMock).toHaveBeenCalled());
  return { onStart, user: userEvent.setup() };
}

describe('choosing a mode', () => {
  it('starts in prompt mode, which is what Wave 1 shipped', async () => {
    await setup();
    expect(screen.getByRole('radio', { name: /Grounding DINO/ })).toBeChecked();
    expect(screen.getByLabelText(/Prompt/)).toBeInTheDocument();
  });

  it('hides the prompt field in head mode', async () => {
    // Not cosmetic: a visible prompt field in head mode implies the phrase is used, and
    // the whole decision was that choosing a head *replaces* it.
    const { user } = await setup();

    await user.click(screen.getByRole('radio', { name: /head you trained/ }));

    expect(screen.queryByLabelText(/Prompt/)).not.toBeInTheDocument();
  });

  it('shows the head picker only in head mode', async () => {
    const { user } = await setup();
    expect(screen.queryByRole('group', { name: 'Annotate with' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: /head you trained/ }));

    expect(await screen.findByRole('group', { name: 'Annotate with' })).toBeInTheDocument();
  });

  it('renames the threshold to match what it thresholds', async () => {
    const { user } = await setup();
    expect(screen.getByText(/Box threshold/)).toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: /head you trained/ }));

    expect(screen.getByText(/Score threshold/)).toBeInTheDocument();
  });
});

describe('the config it emits', () => {
  it('describes a head source in head mode', async () => {
    const { onStart, user } = await setup();

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Thermal');
    await user.click(screen.getByRole('radio', { name: /head you trained/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    expect(onStart.mock.calls[0]?.[0].source).toMatchObject({
      kind: 'head',
      instanceId: 'h1',
      backboneId: 'dinov2-small',
    });
  });

  it('carries no prompt fields on a head source', async () => {
    // The union is what makes "a prompt and a head" unrepresentable; this checks the
    // form actually builds one arm of it rather than a merged object.
    const { onStart, user } = await setup();

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Thermal');
    await user.click(screen.getByRole('radio', { name: /head you trained/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    expect(onStart.mock.calls[0]?.[0].source).not.toHaveProperty('prompt');
  });

  it('refuses to start head mode with no head to run', async () => {
    const { onStart, user } = await setup([]);

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Thermal');
    await user.click(screen.getByRole('radio', { name: /head you trained/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    expect(onStart).not.toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toHaveTextContent(/train a detection head/i);
  });
});

describe('the head selection is derived, not seeded', () => {
  it('uses the first compatible head once the fetch resolves', async () => {
    // The regression: a `useState(heads[0]?.id ?? '')` runs before this response lands and
    // stays '', so the radio renders checked while the submitted id is empty.
    const { onStart, user } = await setup([head({ id: 'first' }), head({ id: 'second' })]);

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Thermal');
    await user.click(screen.getByRole('radio', { name: /head you trained/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    expect(onStart.mock.calls[0]?.[0].source.instanceId).toBe('first');
  });

  it("prefers the user's pick over the default", async () => {
    const { onStart, user } = await setup([
      head({ id: 'first', name: 'First head' }),
      head({ id: 'second', name: 'Second head' }),
    ]);

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Thermal');
    await user.click(screen.getByRole('radio', { name: /head you trained/ }));
    await user.click(await screen.findByRole('radio', { name: /Second head/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    expect(onStart.mock.calls[0]?.[0].source.instanceId).toBe('second');
  });

  it('ignores a head that cannot propose boxes when defaulting', async () => {
    // `render_hint`, never `task` — the segmenter below keeps task 'detection' so a
    // filter written against the wrong field would pick it and pass.
    const { onStart, user } = await setup([
      head({ id: 'segmenter', render_hint: 'masks' }),
      head({ id: 'detector' }),
    ]);

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Thermal');
    await user.click(screen.getByRole('radio', { name: /head you trained/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    expect(onStart.mock.calls[0]?.[0].source.instanceId).toBe('detector');
  });
});

describe('telling you which prompt you are looking at (doc 39)', () => {
  it('explains Grounding DINO syntax in prompt mode', async () => {
    await setup();
    expect(screen.getByText(/a bolt\. a nut\. a washer\./)).toBeInTheDocument();
  });

  it('associates the hint with the field rather than burying it in the label', () => {
    // Inside a <label> the paragraph would join the field's accessible name and be read
    // out on every focus. `aria-describedby` is announced once, on demand.
    render(<SessionSetup onStart={vi.fn()} />);
    expect(screen.getByLabelText(/Prompt/)).toHaveAttribute('aria-describedby', 'prompt-hint');
  });

  it('replaces the syntax hint with the head explanation in head mode', async () => {
    const { user } = await setup();

    await user.click(screen.getByRole('radio', { name: /head you trained/ }));

    expect(screen.queryByText(/a bolt\. a nut\. a washer\./)).not.toBeInTheDocument();
    expect(await screen.findByText(/No prompt here/)).toBeInTheDocument();
  });

  it("names the selected head's own classes", async () => {
    // The question a missing field raises is "so what will it look for?" — answering it
    // is the difference between explaining an absence and just noting one.
    const { user } = await setup([head({ class_names: ['dog', 'person'] })]);

    await user.click(screen.getByRole('radio', { name: /head you trained/ }));

    expect(await screen.findByText(/dog, person/)).toBeInTheDocument();
  });
});


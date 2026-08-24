/**
 * Proposing with a general detector (doc 42).
 *
 * Split from `SessionSetup.test.tsx` at the project's 300-line gate. This is the mode a
 * first-time user can actually reach — nothing trained, no phrase to guess — so it is worth
 * reading on its own.
 */

import { screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { DETECTOR, fetchMock, head, setup } from './sessionSetup.testkit';

beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});

describe('proposing with a general detector (doc 42)', () => {
  it('offers it as a mode', async () => {
    await setup();
    expect(screen.getByRole('radio', { name: /general detector/ })).toBeInTheDocument();
  });

  it('emits a foundation source', async () => {
    const { onStart, user } = await setup();

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Things');
    await user.click(screen.getByRole('radio', { name: /general detector/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    expect(onStart.mock.calls[0]?.[0].source).toMatchObject({
      kind: 'foundation',
      foundationId: 'rf-detr-nano',
    });
  });

  it('names no backbone, because a general detector has none to name', async () => {
    const { onStart, user } = await setup();

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Things');
    await user.click(screen.getByRole('radio', { name: /general detector/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    await waitFor(() => expect(onStart).toHaveBeenCalled());
    expect(onStart.mock.calls[0]?.[0].source).not.toHaveProperty('backboneId');
  });

  it('never offers a depth model as a box proposer', async () => {
    // `render_hint`, not `task` — a depth model is a foundation model too, and there is
    // nothing here to review a depth map with.
    const { user } = await setup();

    await user.click(screen.getByRole('radio', { name: /general detector/ }));

    expect(await screen.findByRole('radio', { name: /RF-DETR/ })).toBeInTheDocument();
    expect(screen.queryByRole('radio', { name: /Depth Anything/ })).not.toBeInTheDocument();
  });

  it('refuses to start with no detector installed, and says where to get one', async () => {
    const { onStart, user } = await setup([head()], [{ ...DETECTOR, installed: false }]);

    await user.type(screen.getByLabelText(/Image folder/), '/pics');
    await user.type(screen.getByLabelText(/New dataset name/), 'Things');
    await user.click(screen.getByRole('radio', { name: /general detector/ }));
    await user.click(screen.getByRole('button', { name: /Start annotating/ }));

    expect(onStart).not.toHaveBeenCalled();
    expect(await screen.findByRole('alert')).toHaveTextContent(/Admin/);
  });

  it('hides the prompt field, as head mode does', async () => {
    const { user } = await setup();
    await user.click(screen.getByRole('radio', { name: /general detector/ }));
    expect(screen.queryByLabelText(/Prompt/)).not.toBeInTheDocument();
  });
});

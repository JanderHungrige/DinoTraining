/**
 * The Training tab's two modes.
 *
 * This exists because of a discoverability failure, not a logic one. Fine-tuning used to
 * sit at the bottom of this tab under an `<h3>` — below the head form, the progress panel
 * and the list of trained heads — under a tab called "Head Trainer" that named only half
 * of what it did. So the model that actually wins at detection (RF-DETR, mAP 0.96 on rail
 * against 0.5–0.6 for a DINO head) was the one nobody found.
 *
 * What is worth pinning is therefore about *reachability*: both modes are offered before
 * anything is scrolled, exactly one is shown at a time, and the head path stays the
 * default because it is the cheaper one and the one a first-time user has the data for.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as foundation from '../api/foundation';
import * as heads from '../api/headInstances';
import * as trainerOptions from '../hooks/useTrainerOptions';
import { HeadTrainerTab } from './HeadTrainerTab';

vi.mock('../api/foundation');
vi.mock('../api/headInstances');

beforeEach(() => {
  vi.mocked(heads.listHeadInstances).mockResolvedValue([]);
  vi.mocked(foundation.listFoundations).mockResolvedValue([]);
  vi.spyOn(trainerOptions, 'useTrainerOptions').mockReturnValue({
    datasets: [],
    backbones: [],
    headTypes: [],
    loading: false,
    error: null,
  } as unknown as ReturnType<typeof trainerOptions.useTrainerOptions>);
});

async function renderTab() {
  render(<HeadTrainerTab />);
  await waitFor(() => expect(heads.listHeadInstances).toHaveBeenCalled());
  return userEvent.setup();
}

describe('finding the two things this tab does', () => {
  it('offers both before anything is scrolled', async () => {
    // The whole point. Fine-tuning below three panels was the same as not being there.
    await renderTab();

    expect(screen.getByRole('radio', { name: /DINO head/ })).toBeInTheDocument();
    expect(screen.getByRole('radio', { name: /Fine-tune a model/ })).toBeInTheDocument();
  });

  it('is a radio group, so the two read as exclusive without hand-written ARIA', async () => {
    await renderTab();

    expect(screen.getByRole('group', { name: /What to train/ })).toBeInTheDocument();
  });

  it('says what each is for, because the name alone does not decide it', async () => {
    await renderTab();

    expect(screen.getByText(/Frozen backbone, trains in minutes/)).toBeInTheDocument();
    expect(screen.getByText(/much stronger at boxes/)).toBeInTheDocument();
  });
});

describe('which one is showing', () => {
  it('starts on the head path', async () => {
    // The cheaper one, the one the rest of the app is built around, and the one a
    // first-time user has the data for.
    await renderTab();

    expect(screen.getByRole('radio', { name: /DINO head/ })).toBeChecked();
    expect(screen.getByText(/The backbone stays frozen/)).toBeInTheDocument();
  });

  it('switches to fine-tuning and puts the head form away', async () => {
    const user = await renderTab();

    await user.click(screen.getByRole('radio', { name: /Fine-tune a model/ }));

    expect(screen.queryByText(/The backbone stays frozen/)).not.toBeInTheDocument();
    expect(screen.getByText(/Trains the whole model on your classes/)).toBeInTheDocument();
  });

  it('says why fine-tuning is worth the wait, with the number', async () => {
    // "Slower" on its own reads as a drawback. Slower *and* 0.96 against 0.5-0.6 is a
    // trade, and it is the trade this tab exists to put in front of someone.
    const user = await renderTab();

    await user.click(screen.getByRole('radio', { name: /Fine-tune a model/ }));

    expect(screen.getByText(/0\.96 on rail/)).toBeInTheDocument();
  });

  it('goes back', async () => {
    const user = await renderTab();

    await user.click(screen.getByRole('radio', { name: /Fine-tune a model/ }));
    await user.click(screen.getByRole('radio', { name: /DINO head/ }));

    expect(screen.getByText(/The backbone stays frozen/)).toBeInTheDocument();
  });

  it('keeps the trained-head list on the head path only', async () => {
    // It is the output of head training. Beside the fine-tune form it would be a list of
    // the wrong kind of thing — a fine-tune produces a model, listed in the Library.
    const user = await renderTab();
    expect(screen.getByRole('heading', { name: 'Trained heads' })).toBeInTheDocument();

    await user.click(screen.getByRole('radio', { name: /Fine-tune a model/ }));

    expect(screen.queryByRole('heading', { name: 'Trained heads' })).not.toBeInTheDocument();
  });
});

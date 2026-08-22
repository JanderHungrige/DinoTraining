/**
 * The library (doc 51).
 *
 * The risks are all about deletion: hitting it by accident, hitting the wrong one, and a
 * list that keeps claiming something exists after the delete half-failed.
 */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as datasets from '../api/datasets';
import * as foundation from '../api/foundation';
import * as heads from '../api/headInstances';
import { LibraryTab } from './LibraryTab';

vi.mock('../api/datasets');
vi.mock('../api/foundation');
vi.mock('../api/headInstances');

const DATASET = {
  id: 'd1',
  name: 'Chess pieces',
  created_at: '2026-01-01T00:00:00Z',
  prompt: null,
  copy_images: false,
  counts: { images: 289, positive: 100, negative: 2, unclear: 1 },
} as unknown as datasets.DatasetInfo;

const HEAD = {
  id: 'h1',
  name: 'Chess detector',
  summary: 'Object detection · 13 classes · trained on 1 dataset',
  dataset_ids: ['d1'],
  backbone_id: 'dinov2-small',
} as unknown as heads.HeadInstanceInfo;

const TUNED = {
  id: 'f1',
  title: 'Rail RF-DETR',
  description: 'fine-tuned from rf-detr-nano · 3 classes',
  licence: 'Apache-2.0',
  approx_size_mb: 0,
} as unknown as foundation.FoundationInfo;

const CATALOGUE = { ...TUNED, id: 'rf-detr-nano', title: 'RF-DETR', approx_size_mb: 116 };

beforeEach(() => {
  // Counts accumulate across tests otherwise, and two assertions here are about how
  // many times a list was re-read.
  vi.clearAllMocks();
  vi.mocked(datasets.listDatasets).mockResolvedValue([DATASET]);
  vi.mocked(heads.listHeadInstances).mockResolvedValue([HEAD]);
  vi.mocked(foundation.listFoundations).mockResolvedValue([TUNED, CATALOGUE]);
  vi.mocked(datasets.deleteDataset).mockResolvedValue(undefined);
  vi.mocked(heads.deleteHeadInstance).mockResolvedValue({ deleted: true } as never);
  vi.mocked(foundation.deleteFoundationInstance).mockResolvedValue(undefined);
});

describe('what it lists', () => {
  it('shows datasets, heads and fine-tuned models together', async () => {
    render(<LibraryTab />);
    expect(await screen.findByText('Chess pieces')).toBeInTheDocument();
    expect(screen.getByText('Chess detector')).toBeInTheDocument();
    expect(screen.getByText('Rail RF-DETR')).toBeInTheDocument();
  });

  it('does not list a catalogue model as something you made', async () => {
    // Those are downloads managed in Admin / Models; the backend refuses to delete one,
    // so offering it here would be a button whose only outcome is a 404.
    render(<LibraryTab />);
    await screen.findByText('Rail RF-DETR');
    expect(screen.queryByText('RF-DETR')).not.toBeInTheDocument();
  });

  it('resolves a head dataset id to its name', async () => {
    // An id tells the user nothing about which data the head saw.
    render(<LibraryTab />);
    expect(await screen.findByText(/from Chess pieces/)).toBeInTheDocument();
  });

  it('uses the head own summary rather than composing a second description', async () => {
    render(<LibraryTab />);
    expect(await screen.findByText(HEAD.summary)).toBeInTheDocument();
  });

  it('says what to do when a section is empty', async () => {
    vi.mocked(heads.listHeadInstances).mockResolvedValue([]);
    render(<LibraryTab />);
    expect(await screen.findByText(/Train one in the Head Trainer/)).toBeInTheDocument();
  });
});

describe('when a list fails', () => {
  it('names which one, and still shows the others', async () => {
    // The user is here to clean up and needs to know which list is incomplete before
    // deleting anything based on it.
    vi.mocked(heads.listHeadInstances).mockRejectedValue(new Error('nope'));
    render(<LibraryTab />);
    expect(await screen.findByRole('alert')).toHaveTextContent(/heads/);
    expect(screen.getByText('Chess pieces')).toBeInTheDocument();
  });
});

describe('deleting', () => {
  it('asks before it deletes', async () => {
    const user = userEvent.setup();
    render(<LibraryTab />);
    await user.click(await screen.findByLabelText('Delete Chess pieces'));
    expect(datasets.deleteDataset).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: /Delete “Chess pieces”/ })).toBeInTheDocument();
  });

  it('names the item in the confirmation', async () => {
    // This list is full of similarly-named things; a confirm() cannot say which one.
    const user = userEvent.setup();
    render(<LibraryTab />);
    await user.click(await screen.findByLabelText('Delete Chess detector'));
    expect(screen.getByRole('button', { name: /Delete “Chess detector”/ })).toBeInTheDocument();
  });

  it('lets you back out', async () => {
    const user = userEvent.setup();
    render(<LibraryTab />);
    await user.click(await screen.findByLabelText('Delete Chess pieces'));
    await user.click(screen.getByRole('button', { name: 'Keep' }));
    expect(datasets.deleteDataset).not.toHaveBeenCalled();
    expect(screen.getByLabelText('Delete Chess pieces')).toBeInTheDocument();
  });

  it('deletes the right kind for the right row', async () => {
    const user = userEvent.setup();
    render(<LibraryTab />);
    await user.click(await screen.findByLabelText('Delete Rail RF-DETR'));
    await user.click(screen.getByRole('button', { name: /Delete “Rail RF-DETR”/ }));
    await waitFor(() => expect(foundation.deleteFoundationInstance).toHaveBeenCalledWith('f1'));
    expect(datasets.deleteDataset).not.toHaveBeenCalled();
    expect(heads.deleteHeadInstance).not.toHaveBeenCalled();
  });

  it('re-reads the lists afterwards', async () => {
    const user = userEvent.setup();
    render(<LibraryTab />);
    await user.click(await screen.findByLabelText('Delete Chess pieces'));
    await user.click(screen.getByRole('button', { name: /Delete “Chess pieces”/ }));
    await waitFor(() => expect(datasets.listDatasets).toHaveBeenCalledTimes(2));
  });

  it('says so and re-reads when the delete fails', async () => {
    // A delete that half-failed leaves the list lying about what is on disk, on the one
    // screen where that matters most.
    vi.mocked(datasets.deleteDataset).mockRejectedValue(new Error('locked'));
    const user = userEvent.setup();
    render(<LibraryTab />);
    await user.click(await screen.findByLabelText('Delete Chess pieces'));
    await user.click(screen.getByRole('button', { name: /Delete “Chess pieces”/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/what is really there/);
    await waitFor(() => expect(datasets.listDatasets).toHaveBeenCalledTimes(2));
  });

  it('warns that deleting is permanent', async () => {
    render(<LibraryTab />);
    expect(await screen.findByText(/has to be retrained/)).toBeInTheDocument();
  });

  it('counts what each section holds', async () => {
    render(<LibraryTab />);
    const heading = await screen.findByRole('heading', { name: /Datasets/ });
    expect(within(heading).getByText('1')).toBeInTheDocument();
  });
});

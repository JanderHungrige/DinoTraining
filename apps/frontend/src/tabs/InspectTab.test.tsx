import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { InspectTab } from './InspectTab';

vi.mock('../api/datasets', async () => {
  const actual = await vi.importActual<typeof import('../api/datasets')>('../api/datasets');
  return { ...actual, listDatasets: vi.fn(), listDatasetImages: vi.fn() };
});
vi.mock('../api/datasetSequences', async () => {
  const actual =
    await vi.importActual<typeof import('../api/datasetSequences')>('../api/datasetSequences');
  return { ...actual, listDatasetSequences: vi.fn() };
});
vi.mock('../api/video', async () => {
  const actual = await vi.importActual<typeof import('../api/video')>('../api/video');
  return { ...actual, probeSequence: vi.fn() };
});

const datasets = await import('../api/datasets');
const sequences = await import('../api/datasetSequences');
const video = await import('../api/video');

const RIDE = '/v/ride.mp4';

beforeEach(() => {
  vi.mocked(datasets.listDatasets).mockResolvedValue([
    { id: 'd1', name: 'Bolts', counts: { images: 4, masks: 0 } } as never,
    { id: 'd2', name: 'Rail', counts: { images: 2, masks: 0 } } as never,
  ]);
  vi.mocked(datasets.listDatasetImages).mockResolvedValue([
    { path: '/d2/f2.jpg', width: 64, height: 48, boxes: [] },
  ]);
  vi.mocked(sequences.listDatasetSequences).mockImplementation(async (id: string) => ({
    dataset_id: id,
    class_names: ['signal'],
    sequences: [
      {
        source: RIDE,
        kind: 'video',
        frames: [0, 2, 4, 6].map((index) => ({
          index,
          path: `/d2/f${index}.jpg`,
          annotated: index === 2,
          classes: index === 2 ? ['signal'] : [],
        })),
      },
    ],
    loose: [{ index: 0, path: '/d2/photo.jpg', annotated: true, classes: [] }],
  }));
  vi.mocked(video.probeSequence).mockResolvedValue({
    source: RIDE, kind: 'video', frames: 8, fps: 10, duration: 0.8, width: 64, height: 48,
  });
});

describe('InspectTab (doc 74)', () => {
  it('opens the dataset and sequence it was sent to, over what was remembered', async () => {
    localStorage.setItem('dinotraining.v1.inspect.dataset', '"d1"');
    render(<InspectTab request={{ datasetId: 'd2', sequence: RIDE, nonce: 1 }} />);

    await waitFor(() => expect(sequences.listDatasetSequences).toHaveBeenCalledWith('d2', expect.anything()));
    expect(await screen.findByText('1 / 4 · frame 0 · not annotated')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Play' })).toHaveValue(RIDE);
  });

  it('offers the loose images as their own track', async () => {
    render(<InspectTab request={{ datasetId: 'd2', sequence: null, nonce: 1 }} />);
    const play = await screen.findByRole('combobox', { name: 'Play' });
    expect([...play.querySelectorAll('option')].map((o) => o.textContent)).toEqual([
      'ride.mp4 · 4 frames, 1 annotated',
      'Images not in a sequence · 1',
    ]);
  });

  it('plays a video saved every 2nd frame at half its rate', async () => {
    render(<InspectTab request={{ datasetId: 'd2', sequence: RIDE, nonce: 1 }} />);
    // 10 fps source, frames 0, 2, 4, 6: every 2nd, so 5 fps keeps real time.
    await waitFor(() => expect(screen.getByRole('spinbutton')).toHaveValue(5));
  });

  it('steps through frames and says which ones hold annotations', async () => {
    const user = userEvent.setup();
    render(<InspectTab request={{ datasetId: 'd2', sequence: RIDE, nonce: 1 }} />);
    await screen.findByText('1 / 4 · frame 0 · not annotated');
    await user.click(screen.getByRole('button', { name: 'Frame ▶' }));
    expect(screen.getByText('2 / 4 · frame 2')).toBeInTheDocument();
  });

  it('falls back to the first dataset with images when nothing points anywhere', async () => {
    render(<InspectTab request={null} />);
    await waitFor(() => expect(sequences.listDatasetSequences).toHaveBeenCalledWith('d1', expect.anything()));
  });

  it('clicking a bar and pressing First jumps to that class\'s first frame (doc 75)', async () => {
    const user = userEvent.setup();
    render(<InspectTab request={{ datasetId: 'd2', sequence: RIDE, nonce: 1 }} />);
    await screen.findByText('1 / 4 · frame 0 · not annotated');

    await user.click(screen.getByRole('button', { name: 'signal: on 1 of 4 frames' }));
    await user.click(screen.getByRole('button', { name: /first/i }));
    expect(screen.getByText('2 / 4 · frame 2')).toBeInTheDocument();
  });
});


import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { estimateMegabytes, framesInRange, VideoSourceFields } from './VideoSourceFields';

vi.mock('../api/video', async () => {
  const actual = await vi.importActual<typeof import('../api/video')>('../api/video');
  return { ...actual, probeSequence: vi.fn() };
});
const video = await import('../api/video');

const INFO = {
  source: '/v/track.mp4',
  kind: 'video' as const,
  frames: 1000,
  fps: 30,
  duration: 33.3,
  width: 1920,
  height: 1080,
};

describe('VideoSourceFields (doc 73)', () => {
  it('counts the frames a range really gives', () => {
    expect(framesInRange(1000, { start: 0, count: 120, stride: 1 })).toBe(120);
    expect(framesInRange(1000, { start: 990, count: 120, stride: 1 })).toBe(10);
    expect(framesInRange(1000, { start: 0, count: 5000, stride: 10 })).toBe(100);
    expect(framesInRange(1000, { start: 1000, count: 5, stride: 1 })).toBe(0);
  });

  it('estimates the disk it will take, from the frame size', () => {
    // 120 × 1920 × 1080 × 0.2 bytes ≈ 50 MB.
    expect(estimateMegabytes(INFO, 120)).toBe(50);
  });

  it('states the cost before the click, once the video is probed', async () => {
    vi.mocked(video.probeSequence).mockResolvedValue(INFO);
    render(
      <VideoSourceFields
        id="gen"
        path="/v/track.mp4"
        range={{ start: 0, count: 120, stride: 2 }}
        disabled={false}
        onChange={vi.fn()}
      />,
    );
    const status = await screen.findByRole('status', {}, { timeout: 2000 });
    expect(status).toHaveTextContent('1,000 frames at 30 fps');
    expect(status).toHaveTextContent('Decodes 120 frames into the dataset — about 50 MB');
  });

  it('says so when the path is not a video it can decode', () => {
    render(
      <VideoSourceFields
        id="gen"
        path="/v/notes.txt"
        range={{ start: 0, count: 1, stride: 1 }}
        disabled={false}
        onChange={vi.fn()}
      />,
    );
    expect(screen.getByText(/Not a video this app can decode/)).toBeInTheDocument();
    expect(video.probeSequence).not.toHaveBeenCalledWith('/v/notes.txt', expect.anything());
  });
});

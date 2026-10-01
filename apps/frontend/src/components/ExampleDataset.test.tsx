import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExampleDataset as Example, ImportJob } from '../api/datasetImport';
import { renderInGerman } from '../i18n/testing';

const api = vi.hoisted(() => ({
  list: vi.fn<() => Promise<readonly Example[]>>(),
  start: vi.fn<(id: string, variant: string) => Promise<ImportJob>>(),
  job: vi.fn<(id: string) => Promise<ImportJob>>(),
}));
vi.mock('../api/datasetImport', () => ({
  listExamples: api.list,
  importExample: api.start,
  getImportJob: api.job,
}));

import { ExampleDataset } from './ExampleDataset';

const OSDAR: Example = {
  example_id: 'osdar23', sequence: '3_fire_site_3.4', download_bytes: 763_518_017,
  page: 'https://data.fid-move.de/dataset/osdar23/resource/068947d5', licence: 'CC BY-SA 3.0 DE', annotations_licence: 'CC0 1.0',
  licence_url: 'https://creativecommons.org/licenses/by-sa/3.0/de/', attribution: 'DZSF…', downloaded: [], running_job: null,
};

function job(over: Partial<ImportJob>): ImportJob {
  return { job_id: 'e1', path: '', state: 'running', phase: 'download', done: 0, total: 763_518_017, current: '', result: null, error: null, ...over };
}

beforeEach(() => {
  api.list.mockReset().mockResolvedValue([OSDAR]);
  api.start.mockReset();
  api.job.mockReset();
});

describe('ExampleDataset (doc 138)', () => {
  it('offers both variants with the download size, the authors and the licence', async () => {
    render(<ExampleDataset onImported={() => undefined} />);
    expect(await screen.findByRole('button', { name: /Everything: all cameras, lidar, radar/ })).toHaveTextContent('764 MB download · keeps everything');
    expect(screen.getByRole('button', { name: /RGB centre camera only/ })).toHaveTextContent('keeps one camera and its labels');
    expect(screen.getByText(/German Centre for Rail Traffic Research/)).toBeInTheDocument();
    const licence = screen.getByRole('link', { name: /Pictures CC BY-SA 3.0 DE, annotations CC0 1.0/ });
    expect(licence).toHaveAttribute('href', OSDAR.licence_url);
    expect(licence).toHaveAttribute('target', '_blank');
  });

  it('follows the download into the import, then re-reads the list and itself', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onImported = vi.fn();
    api.start.mockResolvedValue(job({ done: 0 }));
    api.job
      .mockResolvedValueOnce(job({ done: 381_000_000, current: 'rgb_center/012.png' }))
      .mockResolvedValueOnce(job({ phase: 'import', done: 50, total: 100, current: '012.png' }))
      .mockResolvedValueOnce(job({
        state: 'complete', phase: 'import',
        result: { dataset_id: 'd1', name: 'OSDaR23 · 3_fire_site_3.4 · RGB centre camera', pictures: 100, annotated_pictures: 100, objects: 900, masks: 0, classes: ['person'], skipped_pictures: 0, skipped_objects: 0 },
      }));
    render(<ExampleDataset onImported={onImported} />);
    fireEvent.click(await screen.findByRole('button', { name: /RGB centre camera only/ }));
    await waitFor(() => expect(api.start).toHaveBeenCalledWith('osdar23', 'rgb-center'));
    expect(screen.getByRole('button', { name: /Everything/ })).toBeDisabled();
    await act(async () => { await vi.advanceTimersByTimeAsync(800); });
    expect(screen.getByText('Downloading… 381 of 764 MB · rgb_center/012.png')).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(800); });
    expect(screen.getByText(/Importing… 50 of 100/)).toBeInTheDocument();
    await act(async () => { await vi.advanceTimersByTimeAsync(800); });
    expect(screen.getByText('“OSDaR23 · 3_fire_site_3.4 · RGB centre camera” imported.')).toBeInTheDocument();
    expect(onImported).toHaveBeenCalledTimes(1);
    expect(api.list).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });

  it('says an already downloaded variant imports again, and shows a refusal', async () => {
    api.list.mockResolvedValue([{ ...OSDAR, downloaded: ['full'] }]);
    api.start.mockRejectedValue(new Error('Not enough free disk space: 1752 MB needed, 900 MB free.'));
    render(<ExampleDataset onImported={() => undefined} />);
    expect(await screen.findByRole('button', { name: /Everything/ })).toHaveTextContent('already downloaded, imports again');
    fireEvent.click(screen.getByRole('button', { name: /Everything/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('Not enough free disk space');
  });

  it('follows a download that was already running when the page opened', async () => {
    api.list.mockResolvedValue([{ ...OSDAR, running_job: 'e1' }]);
    api.job.mockResolvedValue(job({ done: 120_000_000, current: 'rgb_center/003.png' }));
    render(<ExampleDataset onImported={() => undefined} />);
    expect(await screen.findByText('Downloading… 120 of 764 MB · rgb_center/003.png')).toBeInTheDocument();
    expect(api.job).toHaveBeenCalledWith('e1', expect.anything());
    expect(screen.getByRole('button', { name: /RGB centre camera only/ })).toBeDisabled();
  });

  it('speaks German', async () => {
    renderInGerman(<ExampleDataset onImported={() => undefined} />);
    expect(await screen.findByRole('button', { name: /Nur die mittlere RGB-Kamera/ })).toHaveTextContent('764 MB Download');
    expect(screen.getByText('Beispieldatensatz: OSDaR23 (Bahn)')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Bilder CC BY-SA 3.0 DE, Annotationen CC0 1.0/ })).toBeInTheDocument();
  });
});

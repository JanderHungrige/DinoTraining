import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { act } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { CloudConnection, LinkDetection } from '../api/cloud';
import type { Detection, ImportJob } from '../api/datasetImport';
import { renderInGerman } from '../i18n/testing';

const api = vi.hoisted(() => ({
  list: vi.fn<() => Promise<CloudConnection[]>>(),
  detect: vi.fn<(id: string, bucket: string, prefix: string) => Promise<LinkDetection>>(),
  start: vi.fn<(link: string, name: string, description: string | null) => Promise<ImportJob>>(),
  job: vi.fn<(id: string) => Promise<ImportJob>>(),
}));
vi.mock('../api/cloud', () => ({ listConnections: api.list, detectLink: api.detect, startLink: api.start }));
vi.mock('../api/datasetImport', () => ({ getImportJob: api.job }));

import { CloudLink } from './CloudLink';

const CONNECTIONS: CloudConnection[] = [
  { id: 'c1', name: 'Lab S3', kind: 's3', endpoint: null, region: null, account: null, created_at: '', secrets_set: ['access_key'] },
  { id: 'c2', name: 'Team Azure', kind: 'azure', endpoint: null, region: null, account: 'team', created_at: '', secrets_set: ['account_key'] },
];
const COCO: Detection = {
  path: 's3://photos/rail', kind: 'coco', name: 'rail', pictures: 4, videos: 0, annotation_files: 2, annotated_pictures: 3,
  objects: 3, classes: ['person', 'signal'], annotation_types: ['boxes', 'masks'], splits: ['train', 'val'], convention: 'xywh', notes: [], uncovered: 0,
};
const job = (over: Partial<ImportJob>): ImportJob => ({
  job_id: 'j1', path: 'l1', state: 'running', phase: 'import', done: 0, total: 4, current: '', result: null, error: null, ...over,
});

beforeEach(() => {
  api.list.mockReset().mockResolvedValue(CONNECTIONS);
  api.detect.mockReset().mockResolvedValue({ link_id: 'l1', detection: COCO });
  api.start.mockReset().mockResolvedValue(job({}));
  api.job.mockReset();
});

describe('CloudLink (doc 148)', () => {
  it('checks a bucket on the first connection by default, shows the summary, and links', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const onLinked = vi.fn();
    api.job.mockResolvedValue(job({ state: 'complete', done: 4, result: { dataset_id: 'd1', name: 'Rail (cloud)', pictures: 4, annotated_pictures: 3, objects: 3, masks: 2, classes: [], skipped_pictures: 0, skipped_objects: 0 } }));
    render(<CloudLink onLinked={onLinked} />);
    const check = await screen.findByRole('button', { name: 'Check' });
    expect(check).toBeDisabled(); // no bucket yet
    fireEvent.change(screen.getByRole('textbox', { name: 'Bucket or container' }), { target: { value: 'photos' } });
    fireEvent.change(screen.getByRole('textbox', { name: /prefix/ }), { target: { value: 'rail' } });
    fireEvent.click(check);
    await screen.findByText(/Found:/);
    expect(api.detect).toHaveBeenCalledWith('c1', 'photos', 'rail');
    fireEvent.change(screen.getByRole('textbox', { name: 'Name' }), { target: { value: 'Rail (cloud)' } });
    fireEvent.click(screen.getByRole('button', { name: 'Link' }));
    await waitFor(() => expect(api.start).toHaveBeenCalledWith('l1', 'Rail (cloud)', null));
    await act(async () => { await vi.advanceTimersByTimeAsync(800); });
    expect(await screen.findByText('“Rail (cloud)” imported.')).toBeInTheDocument();
    expect(onLinked).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });

  it('uses the connection the user picks, and says why a check was refused', async () => {
    api.detect.mockRejectedValue(new Error('photos does not exist, or this account cannot see it.'));
    render(<CloudLink onLinked={() => undefined} />);
    fireEvent.change(await screen.findByRole('combobox', { name: 'Connection' }), { target: { value: 'c2' } });
    fireEvent.change(screen.getByRole('textbox', { name: 'Bucket or container' }), { target: { value: 'photos' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('does not exist');
    expect(api.detect).toHaveBeenCalledWith('c2', 'photos', '');
  });

  it('points to Cloud storage when there is no connection yet, in German', async () => {
    api.list.mockResolvedValue([]);
    renderInGerman(<CloudLink onLinked={() => undefined} />);
    expect(await screen.findByText(/Leg zuerst unten unter „Cloud-Speicher“ eine Verbindung an/)).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });
});

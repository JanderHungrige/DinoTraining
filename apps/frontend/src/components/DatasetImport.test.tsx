import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { renderInGerman } from '../i18n/testing';
import type { Detection, ImportJob } from '../api/datasetImport';

const api = vi.hoisted(() => ({
  detect: vi.fn<(path: string) => Promise<Detection>>(),
  start: vi.fn<(request: unknown) => Promise<ImportJob>>(),
  job: vi.fn<(id: string) => Promise<ImportJob>>(),
}));
vi.mock('../api/datasetImport', () => ({
  detectDataset: api.detect,
  startImport: api.start,
  getImportJob: api.job,
}));

import { DatasetImport } from './DatasetImport';

const YOLO: Detection = {
  path: '/data/cars', kind: 'yolo', name: 'cars', pictures: 3, videos: 0, annotation_files: 1,
  annotated_pictures: 3, objects: 3, classes: ['car', 'person'], annotation_types: ['boxes', 'masks'],
  splits: ['train'], convention: 'xywh', notes: ['uncovered'], uncovered: 2,
};

function job(over: Partial<ImportJob>): ImportJob {
  return { job_id: 'j1', path: '/data/cars', state: 'running', phase: 'import', done: 0, total: 3, current: '', result: null, error: null, ...over };
}

beforeEach(() => {
  api.detect.mockReset();
  api.start.mockReset();
  api.job.mockReset();
});

async function detectCars(): Promise<void> {
  fireEvent.change(screen.getByRole('textbox'), { target: { value: '/data/cars' } });
  fireEvent.click(screen.getByRole('button', { name: 'Check the folder' }));
  await screen.findByText(/Found:/);
}

describe('DatasetImport (doc 136)', () => {
  it('shows what the folder holds before importing', async () => {
    api.detect.mockResolvedValue(YOLO);
    render(<DatasetImport onImported={vi.fn()} />);
    await detectCars();
    expect(api.detect).toHaveBeenCalledWith('/data/cars');
    expect(screen.getByText('YOLO')).toBeInTheDocument();
    expect(screen.getByText('3 pictures · 3 annotated · 3 objects · 2 classes · boxes, masks · splits: train')).toBeInTheDocument();
    expect(screen.getByText('car, person')).toBeInTheDocument();
    expect(screen.getByText(/2 pictures are in no annotation file/)).toBeInTheDocument();
  });

  it('names it after the folder unless the user types a name, and sends the description', async () => {
    api.detect.mockResolvedValue(YOLO);
    api.start.mockImplementation(() => new Promise(() => undefined));
    render(<DatasetImport onImported={vi.fn()} />);
    await detectCars();
    const name = screen.getByLabelText('Name');
    expect(name).toHaveValue('cars');
    fireEvent.change(name, { target: { value: 'Cars 2026' } });
    fireEvent.change(screen.getByLabelText('Description (optional)'), { target: { value: 'From Roboflow' } });
    fireEvent.click(screen.getByRole('button', { name: 'Import' }));
    expect(api.start).toHaveBeenCalledWith({ path: '/data/cars', name: 'Cars 2026', description: 'From Roboflow', copy_images: false });
  });

  it('follows the job and tells the list to re-read when it is done', async () => {
    api.detect.mockResolvedValue(YOLO);
    api.start.mockResolvedValue(job({}));
    const done = job({
      state: 'complete', done: 3,
      result: { dataset_id: 'd1', name: 'cars', pictures: 3, annotated_pictures: 3, objects: 3, masks: 1, classes: ['car'], skipped_pictures: 0, skipped_objects: 1 },
    });
    api.job.mockResolvedValue(done);
    const onImported = vi.fn();
    render(<DatasetImport onImported={onImported} />);
    await detectCars();
    await act(async () => fireEvent.click(screen.getByRole('button', { name: 'Import' })));
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
    await waitFor(() => expect(onImported).toHaveBeenCalledTimes(1), { timeout: 3000 });
    expect(screen.getByText('“cars” imported.')).toBeInTheDocument();
    expect(screen.getByText(/skipped: 0 pictures, 1 objects/)).toBeInTheDocument();
  });

  it('says why when the folder holds nothing it can read', async () => {
    api.detect.mockRejectedValue(new Error('No pictures, videos or annotation files found'));
    render(<DatasetImport onImported={vi.fn()} />);
    fireEvent.change(screen.getByRole('textbox'), { target: { value: '/empty' } });
    fireEvent.click(screen.getByRole('button', { name: 'Check the folder' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('No pictures, videos or annotation files found');
  });

  it('speaks German', () => {
    renderInGerman(<DatasetImport onImported={vi.fn()} />);
    expect(screen.getByRole('heading', { name: 'Datensatz importieren' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Ordner prüfen' })).toBeInTheDocument();
  });
});

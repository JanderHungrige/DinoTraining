import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExportResult, ExportTarget } from '../api/datasetExport';
import { renderInGerman } from '../i18n/testing';
import { readPersisted, writePersisted } from '../lib/persisted';

const api = vi.hoisted(() => ({
  get: vi.fn<(id: string) => Promise<ExportTarget>>(),
  set: vi.fn<(id: string, target: unknown) => Promise<ExportTarget>>(),
  run: vi.fn<(id: string) => Promise<ExportResult>>(),
}));
vi.mock('../api/datasetExport', () => ({
  getExportTarget: api.get,
  setExportTarget: api.set,
  exportDataset: api.run,
}));

import { DatasetExport, LAST_FOLDER, since } from './DatasetExport';

const IN_PLACE: ExportTarget = {
  kind: null, folder: null, include_pictures: false, data_folder: '/data/rail',
  exported_at: null, exported_folder: null, changed: true,
};
const INSIDE: ExportTarget = { ...IN_PLACE, data_folder: null, include_pictures: true };
const RESULT: ExportResult = {
  folder: '/data/rail/dinotraining', pictures: 4, annotated: 3, objects: 3, pictures_copied: 0, written_at: '2026-10-01T12:00:00+00:00',
};

beforeEach(() => {
  api.get.mockReset();
  api.set.mockReset().mockImplementation(async () => IN_PLACE);
  api.run.mockReset().mockResolvedValue(RESULT);
  localStorage.clear();
});

const isString = (value: unknown): value is string => typeof value === 'string';

describe('DatasetExport (doc 143)', () => {
  it('offers "with the data" for pictures outside the app and exports there', async () => {
    api.get.mockResolvedValue(IN_PLACE);
    const onExported = vi.fn();
    render(<DatasetExport datasetId="d1" name="Rail" exportedAt={null} onExported={onExported} />);
    expect(screen.getByText('Not exported yet')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Export Rail' }));
    const now = screen.getByRole('button', { name: 'Export now' });
    expect(now).toBeDisabled(); // nothing chosen until the target has loaded
    await waitFor(() => expect(now).toBeEnabled());
    expect(screen.getByRole('radio', { name: 'With the data (/data/rail)' })).toBeChecked();
    fireEvent.click(now);
    await screen.findByText(/Written to \/data\/rail\/dinotraining: 4 pictures · 3 objects/);
    expect(api.set).toHaveBeenCalledWith('d1', { kind: 'data', folder: null, include_pictures: false });
    expect(onExported).toHaveBeenCalledTimes(1);
  });

  it('asks for a folder when the pictures live inside the app, opening at the last one, and remembers it', async () => {
    api.get.mockResolvedValue(INSIDE);
    writePersisted(LAST_FOLDER, '/backups');
    render(<DatasetExport datasetId="d2" name="Chess" exportedAt={null} onExported={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: 'Export Chess' }));
    await screen.findByText(/live inside the app/);
    expect(screen.queryByRole('radio')).toBeNull();
    const field = screen.getByRole('textbox', { name: 'To a folder' });
    expect(field).toHaveValue('/backups');
    expect(screen.getByRole('checkbox', { name: 'Copy the pictures too' })).toBeChecked();
    fireEvent.change(field, { target: { value: '/backups/chess' } });
    fireEvent.click(screen.getByRole('button', { name: 'Export now' }));
    await waitFor(() => expect(api.run).toHaveBeenCalledWith('d2'));
    expect(api.set).toHaveBeenCalledWith('d2', { kind: 'folder', folder: '/backups/chess', include_pictures: true });
    await waitFor(() => expect(readPersisted(LAST_FOLDER, '', isString)).toBe('/backups/chess'));
  });

  it('saves a linked dataset back into its bucket, without offering to copy pictures (doc 150)', async () => {
    api.get.mockResolvedValue({ ...IN_PLACE, kind: 'data', data_folder: 's3://photos/rail/dinotraining', linked: true });
    render(<DatasetExport datasetId="d3" name="Rail cloud" exportedAt={null} onExported={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: 'Export Rail cloud' }));
    expect(await screen.findByRole('radio', { name: 'With the data (s3://photos/rail/dinotraining)' })).toBeChecked();
    expect(screen.queryByRole('checkbox', { name: 'Copy the pictures too' })).toBeNull();
  });

  it('says why an export was refused', async () => {
    api.get.mockResolvedValue(IN_PLACE);
    api.run.mockRejectedValue(new Error('Cannot write to /data/rail: read-only'));
    render(<DatasetExport datasetId="d1" name="Rail" exportedAt={null} onExported={() => undefined} />);
    fireEvent.click(screen.getByRole('button', { name: 'Export Rail' }));
    const now = screen.getByRole('button', { name: 'Export now' });
    await waitFor(() => expect(now).toBeEnabled());
    fireEvent.click(now);
    expect(await screen.findByRole('alert')).toHaveTextContent('read-only');
  });

  it('words the last export in the reader\'s language', () => {
    const now = Date.parse('2026-10-01T12:03:00Z');
    expect(since('2026-10-01T12:00:00Z', 'en', now)).toBe('3 minutes ago');
    expect(since('2026-09-30T12:00:00Z', 'de', now)).toBe('gestern');
    renderInGerman(<DatasetExport datasetId="d1" name="Rail" exportedAt={new Date(Date.now() - 120_000).toISOString()} onExported={() => undefined} />);
    expect(screen.getByText('Exportiert vor 2 Minuten')).toBeInTheDocument();
  });
});

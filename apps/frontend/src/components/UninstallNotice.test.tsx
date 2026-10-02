import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExportOverview, RunResponse } from '../api/exports';
import { renderInGerman } from '../i18n/testing';

const api = vi.hoisted(() => ({
  overview: vi.fn<() => Promise<ExportOverview>>(),
  run: vi.fn<(reason: string, wait: boolean) => Promise<RunResponse>>(),
}));
vi.mock('../api/exports', () => ({ getExportOverview: api.overview, runExports: api.run }));
const edition = vi.hoisted(() => ({ current: 'installer' as string | null }));
vi.mock('../lib/edition', () => ({ useEdition: () => edition.current }));

import { UninstallNotice } from './UninstallNotice';

const PENDING: ExportOverview = { datasets: 3, no_target: ['Cars', 'Chess'], unexported: ['Rail'], models: 2, model_folder: null };
const DONE: ExportOverview = { ...PENDING, no_target: [], unexported: [], models: 1, model_folder: '/models' };

beforeEach(() => {
  api.overview.mockReset();
  api.run.mockReset().mockResolvedValue({ outcome: 'done', report: null });
  edition.current = 'installer';
});

describe('UninstallNotice (doc 146)', () => {
  it('says what uninstalling removes, and what is not exported yet', async () => {
    api.overview.mockResolvedValue(PENDING);
    render(<UninstallNotice />);
    expect(screen.getByText(/Uninstalling can remove everything inside V-Rex .*Exported annotations and models stay/)).toBeInTheDocument();
    expect(await screen.findByText(/2 datasets have no export yet: Cars, Chess\. Choose where each goes/)).toBeInTheDocument();
    expect(screen.getByText(/1 dataset changed since its export: Rail\./)).toBeInTheDocument();
    expect(screen.getByText(/2 trained models are only in the app/)).toBeInTheDocument();
  });

  it('exports everything now, then reads the state again', async () => {
    api.overview.mockResolvedValueOnce(PENDING).mockResolvedValueOnce(DONE);
    const onExported = vi.fn();
    render(<UninstallNotice onExported={onExported} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Export everything now' }));
    expect(await screen.findByText('All datasets are exported.')).toBeInTheDocument();
    expect(api.run).toHaveBeenCalledWith('manual', true);
    expect(onExported).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/1 trained model; new ones export by themselves\./)).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('offers no export button when nothing has a target to go to', async () => {
    api.overview.mockResolvedValue({ ...PENDING, unexported: [] });
    render(<UninstallNotice />);
    await screen.findByText(/have no export yet/);
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('still warns when the numbers are unavailable, and speaks German', async () => {
    api.overview.mockRejectedValue(new Error('backend starting'));
    renderInGerman(<UninstallNotice />);
    expect(screen.getByText(/Beim Deinstallieren kann alles entfernt werden/)).toBeInTheDocument();
    await waitFor(() => expect(api.overview).toHaveBeenCalled());
    expect(screen.queryByRole('button')).toBeNull();
  });

  it('under the Store, says Windows removes it all without asking (doc 156)', async () => {
    edition.current = 'store';
    api.overview.mockResolvedValue(DONE);
    renderInGerman(<UninstallNotice />);
    expect(screen.getByText(/in Windows deinstallierst, wird alles darin ohne Rückfrage entfernt/)).toBeInTheDocument();
    expect(screen.queryByText(/Anwendungsdaten löschen/)).toBeNull();
    await waitFor(() => expect(api.overview).toHaveBeenCalled());
  });
});

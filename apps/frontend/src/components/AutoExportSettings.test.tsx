import { act, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { AutoReport, ExportSettings, ExportStatus, RunResponse } from '../api/exports';
import { renderInGerman } from '../i18n/testing';

const api = vi.hoisted(() => ({
  settings: vi.fn<() => Promise<ExportSettings>>(),
  put: vi.fn<(settings: ExportSettings) => Promise<ExportSettings>>(),
  status: vi.fn<() => Promise<ExportStatus>>(),
  run: vi.fn<(reason: string, wait: boolean) => Promise<RunResponse>>(),
}));
vi.mock('../api/exports', () => ({
  getExportSettings: api.settings,
  putExportSettings: api.put,
  getExportStatus: api.status,
  runExports: api.run,
  SETTINGS_EVENT: 'dinotraining:export-settings',
}));

import { useAutoExport } from '../hooks/useAutoExport';
import { AutoExportSettings } from './AutoExportSettings';

const CLOSING: AutoReport = {
  started_at: new Date(Date.now() - 3_600_000).toISOString(),
  finished_at: new Date(Date.now() - 3_600_000).toISOString(),
  reason: 'close',
  exported: [{ dataset_id: 'a', name: 'Rail' }],
  unchanged: 2,
  failed: [{ dataset_id: 'b', name: 'Chess', error: 'Cannot write to /Volumes/USB: not mounted' }],
  unfinished: [{ dataset_id: 'c', name: 'Video' }],
  no_target: [{ dataset_id: 'd', name: 'Cars' }],
};

beforeEach(() => {
  api.settings.mockReset().mockResolvedValue({ on_close: true, every_minutes: 0 });
  api.put.mockReset().mockImplementation(async (settings) => settings);
  api.status.mockReset().mockResolvedValue({ running: false, last: CLOSING });
  api.run.mockReset().mockResolvedValue({ outcome: 'done', report: { ...CLOSING, reason: 'manual', failed: [], unfinished: [] } });
});

afterEach(() => vi.useRealTimers());

describe('AutoExportSettings (doc 144)', () => {
  it('names what the last closing did not export, and which datasets have no target', async () => {
    render(<AutoExportSettings onExported={() => undefined} />);
    expect(await screen.findByText('Last run 1 hour ago: 1 exported, 2 unchanged.')).toBeInTheDocument();
    expect(screen.getByText(/Not exported: Chess\. Cannot write to \/Volumes\/USB/)).toBeInTheDocument();
    expect(screen.getByText(/Left for the next run .*: Video\./)).toBeInTheDocument();
    expect(screen.getByText(/No export target yet: Cars\./)).toBeInTheDocument();
  });

  it('saves the settings and tells the interval', async () => {
    const heard = vi.fn();
    window.addEventListener('dinotraining:export-settings', heard);
    render(<AutoExportSettings onExported={() => undefined} />);
    fireEvent.click(await screen.findByRole('checkbox', { name: 'Every' }));
    await waitFor(() => expect(api.put).toHaveBeenCalledWith({ on_close: true, every_minutes: 10 }));
    fireEvent.change(screen.getByRole('spinbutton', { name: 'minutes' }), { target: { value: '25' } });
    await waitFor(() => expect(api.put).toHaveBeenLastCalledWith({ on_close: true, every_minutes: 25 }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'When closing the app' }));
    await waitFor(() => expect(api.put).toHaveBeenLastCalledWith({ on_close: false, every_minutes: 25 }));
    expect(heard).toHaveBeenCalled();
    window.removeEventListener('dinotraining:export-settings', heard);
  });

  it('exports all now and re-reads the list', async () => {
    const onExported = vi.fn();
    render(<AutoExportSettings onExported={onExported} />);
    fireEvent.click(await screen.findByRole('button', { name: 'Export all now' }));
    await waitFor(() => expect(onExported).toHaveBeenCalledTimes(1));
    expect(api.run).toHaveBeenCalledWith('manual', true);
    expect(screen.queryByText(/Not exported: Chess/)).toBeNull(); // the new run replaced the old report
  });

  it('speaks German', async () => {
    renderInGerman(<AutoExportSettings onExported={() => undefined} />);
    expect(await screen.findByText('Automatischer Export')).toBeInTheDocument();
    expect(screen.getByText(/Noch kein Exportziel: Cars\./)).toBeInTheDocument();
  });
});

describe('useAutoExport (doc 144)', () => {
  it('runs in the background every n minutes, and only when switched on', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.settings.mockResolvedValue({ on_close: true, every_minutes: 0 });
    const { unmount } = renderHook(() => useAutoExport());
    await act(async () => { await vi.advanceTimersByTimeAsync(30 * 60_000); });
    expect(api.run).not.toHaveBeenCalled();

    api.settings.mockResolvedValue({ on_close: true, every_minutes: 5 });
    await act(async () => { window.dispatchEvent(new Event('dinotraining:export-settings')); await Promise.resolve(); });
    await act(async () => { await vi.advanceTimersByTimeAsync(10 * 60_000 + 1000); });
    expect(api.run).toHaveBeenCalledTimes(2);
    expect(api.run).toHaveBeenCalledWith('interval', false);
    unmount();
  });
});

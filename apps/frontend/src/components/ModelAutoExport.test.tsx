import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ExportSettings } from '../api/exports';
import { renderInGerman } from '../i18n/testing';
import { writePersisted } from '../lib/persisted';

const api = vi.hoisted(() => ({
  get: vi.fn<() => Promise<ExportSettings>>(),
  put: vi.fn<(settings: ExportSettings) => Promise<ExportSettings>>(),
}));
vi.mock('../api/exports', () => ({ getExportSettings: api.get, putExportSettings: api.put }));

import { ModelAutoExport } from './ModelAutoExport';
import { MODEL_LAST_FOLDER } from './ModelExportActions';

const OFF: ExportSettings = { on_close: true, every_minutes: 0, model_folder: null };

beforeEach(() => {
  localStorage.clear();
  api.get.mockReset().mockResolvedValue(OFF);
  api.put.mockReset().mockImplementation(async (settings) => settings);
});

describe('ModelAutoExport (doc 145)', () => {
  it('is off until a folder is there, then switched on with it, keeping the other settings', async () => {
    render(<ModelAutoExport />);
    const toggle = await screen.findByRole('checkbox', { name: /Export each trained model/ });
    expect(toggle).not.toBeChecked();
    expect(toggle).toBeDisabled(); // no folder yet
    fireEvent.change(screen.getByRole('textbox', { name: 'Folder for trained models' }), { target: { value: '/models' } });
    fireEvent.click(toggle);
    await waitFor(() => expect(api.put).toHaveBeenCalledWith({ on_close: true, every_minutes: 0, model_folder: '/models' }));
    expect(await screen.findByRole('checkbox', { name: /Export each trained model/ })).toBeChecked();
  });

  it('offers the last model folder, and switching off clears only the folder', async () => {
    writePersisted(MODEL_LAST_FOLDER, '/Volumes/backup/models');
    api.get.mockResolvedValue({ ...OFF, every_minutes: 15, model_folder: '/Volumes/backup/models' });
    render(<ModelAutoExport />);
    const toggle = await screen.findByRole('checkbox', { name: /Export each trained model/ });
    expect(toggle).toBeChecked();
    expect(screen.getByRole('textbox')).toHaveValue('/Volumes/backup/models');
    fireEvent.click(toggle);
    await waitFor(() => expect(api.put).toHaveBeenCalledWith({ on_close: true, every_minutes: 15, model_folder: null }));
  });

  it('says why a folder was refused, in German', async () => {
    api.put.mockRejectedValue(new Error('Choose a full folder path'));
    renderInGerman(<ModelAutoExport />);
    fireEvent.change(await screen.findByRole('textbox', { name: 'Ordner für trainierte Modelle' }), { target: { value: 'models' } });
    fireEvent.click(screen.getByRole('checkbox', { name: /Jedes trainierte Modell/ }));
    expect(await screen.findByRole('alert')).toHaveTextContent('full folder path');
  });
});

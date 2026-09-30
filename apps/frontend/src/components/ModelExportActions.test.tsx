import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ModelExportActions } from './ModelExportActions';

vi.mock('../api/modelExports', () => ({
  downloadModelExport: vi.fn(async () => ({ name: 'Screws.zip', blob: new Blob(['zip']) })),
  exportModelTo: vi.fn(async () => ({ path: '/Users/me/Exports/Screws.zip', file: 'Screws.zip' })),
  modelLocation: vi.fn(async () => ({ folder: '/Users/me/Library/DinoTraining/heads' })),
}));
vi.mock('../lib/dialog', () => ({
  hasNativeDialog: vi.fn(() => false),
  pickFolder: vi.fn(async () => '/Users/me/Exports'),
  revealFolder: vi.fn(async () => undefined),
}));
const api = await import('../api/modelExports');
const dialog = await import('../lib/dialog');

beforeEach(() => {
  vi.clearAllMocks();
  URL.createObjectURL = vi.fn(() => 'blob:x');
  URL.revokeObjectURL = vi.fn();
});

describe('ModelExportActions (doc 121)', () => {
  it('in a browser downloads the zip, and offers no folder to open', async () => {
    const user = userEvent.setup();
    render(<ModelExportActions kind="heads" instanceId="h1" name="Screws" />);
    expect(screen.queryByRole('button', { name: 'Show where Screws is' })).not.toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Export Screws' }));
    expect(api.downloadModelExport).toHaveBeenCalledWith('heads', 'h1');
    expect(await screen.findByText('Downloaded: Screws.zip')).toBeInTheDocument();
  });

  it('in the desktop app asks for a folder, writes there, and shows where the model lives', async () => {
    vi.mocked(dialog.hasNativeDialog).mockReturnValue(true);
    const user = userEvent.setup();
    render(<ModelExportActions kind="finetuned" instanceId="f1" name="Outlines" />);
    await user.click(screen.getByRole('button', { name: 'Export Outlines' }));
    expect(api.exportModelTo).toHaveBeenCalledWith('finetuned', 'f1', '/Users/me/Exports');
    expect(await screen.findByText('Written: /Users/me/Exports/Screws.zip')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Show where Outlines is' }));
    expect(dialog.revealFolder).toHaveBeenCalledWith('/Users/me/Library/DinoTraining/heads');
  });

  it('a cancelled folder picker exports nothing', async () => {
    vi.mocked(dialog.hasNativeDialog).mockReturnValue(true);
    vi.mocked(dialog.pickFolder).mockResolvedValueOnce(null);
    const user = userEvent.setup();
    render(<ModelExportActions kind="heads" instanceId="h1" name="Screws" />);
    await user.click(screen.getByRole('button', { name: 'Export Screws' }));
    expect(api.exportModelTo).not.toHaveBeenCalled();
  });
});

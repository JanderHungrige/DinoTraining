/**
 * "Show me where these pictures are" (doc 59).
 *
 * Two things here would mislead rather than merely fail: a button that appears where there
 * is no file manager to open, and a folder that is gone reading as a broken button.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as datasets from '../api/datasets';
import { RevealDatasetButton } from './RevealDatasetButton';

const dialog = vi.hoisted(() => ({
  hasNativeDialog: vi.fn(() => true),
  revealFolder: vi.fn(async () => undefined),
  pickFolder: vi.fn(),
  pickImageFile: vi.fn(),
}));
vi.mock('../lib/dialog', () => dialog);
vi.mock('../api/datasets');

beforeEach(() => {
  vi.clearAllMocks();
  dialog.hasNativeDialog.mockReturnValue(true);
  vi.mocked(datasets.getDatasetFolder).mockResolvedValue({
    folder: '/Users/you/photos',
    exists: true,
    copies: false,
  });
});

describe('when it is offered at all', () => {
  it('appears under Tauri', async () => {
    render(<RevealDatasetButton datasetId="d1" />);
    expect(await screen.findByRole('button', { name: 'Open folder' })).toBeInTheDocument();
  });

  it('is absent in a browser', async () => {
    // Wave 9's web build has no file manager to open. A button that cannot work is worse
    // than no button.
    dialog.hasNativeDialog.mockReturnValue(false);
    const { container } = render(<RevealDatasetButton datasetId="d1" />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });

  it('is absent with no dataset selected', async () => {
    const { container } = render(<RevealDatasetButton datasetId="" />);
    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

describe('opening', () => {
  it('asks the backend where the images are, rather than guessing from the id', async () => {
    // The id only locates the *store* directory, which is empty for a dataset that
    // references the user's own files.
    const user = userEvent.setup();
    render(<RevealDatasetButton datasetId="d1" />);
    await user.click(await screen.findByRole('button', { name: 'Open folder' }));
    await waitFor(() => expect(datasets.getDatasetFolder).toHaveBeenCalledWith('d1'));
  });

  it('reveals the folder the backend named', async () => {
    const user = userEvent.setup();
    render(<RevealDatasetButton datasetId="d1" />);
    await user.click(await screen.findByRole('button', { name: 'Open folder' }));
    await waitFor(() => expect(dialog.revealFolder).toHaveBeenCalledWith('/Users/you/photos'));
  });

  it('says the folder is gone rather than looking broken', async () => {
    // The store still has the boxes; the pictures were moved or deleted. Which of those
    // it is changes what the user does next.
    vi.mocked(datasets.getDatasetFolder).mockResolvedValue({
      folder: '/Users/you/moved',
      exists: false,
      copies: false,
    });
    const user = userEvent.setup();
    render(<RevealDatasetButton datasetId="d1" />);
    await user.click(await screen.findByRole('button', { name: 'Open folder' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('/Users/you/moved');
    expect(dialog.revealFolder).not.toHaveBeenCalled();
  });

  it('reports a failed lookup', async () => {
    vi.mocked(datasets.getDatasetFolder).mockRejectedValue(new Error('nope'));
    const user = userEvent.setup();
    render(<RevealDatasetButton datasetId="d1" />);
    await user.click(await screen.findByRole('button', { name: 'Open folder' }));
    expect(await screen.findByRole('alert')).toHaveTextContent(/Could not open/);
  });

  it('clears a stale message when the dataset changes', async () => {
    // "That folder is gone" left standing against a dataset the user has switched away
    // from is worse than no message.
    vi.mocked(datasets.getDatasetFolder).mockResolvedValue({
      folder: '/gone',
      exists: false,
      copies: false,
    });
    const user = userEvent.setup();
    const { rerender } = render(<RevealDatasetButton datasetId="d1" />);
    await user.click(await screen.findByRole('button', { name: 'Open folder' }));
    await screen.findByRole('alert');

    rerender(<RevealDatasetButton datasetId="d2" />);
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  });

  it('cannot be clicked twice while it is working', async () => {
    let release: (() => void) | undefined;
    vi.mocked(datasets.getDatasetFolder).mockReturnValue(
      new Promise((resolve) => {
        release = () => resolve({ folder: '/x', exists: true, copies: false });
      }),
    );
    const user = userEvent.setup();
    render(<RevealDatasetButton datasetId="d1" />);
    await user.click(await screen.findByRole('button', { name: 'Open folder' }));
    expect(await screen.findByRole('button', { name: 'Opening…' })).toBeDisabled();
    release?.();
  });

  it('respects a disabled parent', async () => {
    render(<RevealDatasetButton datasetId="d1" disabled />);
    expect(await screen.findByRole('button')).toBeDisabled();
  });
});

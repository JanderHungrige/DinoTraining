/**
 * The folder field and its pickers (doc 46).
 *
 * The rule worth pinning is the one a copy would get wrong: **an image means its folder.**
 * A user who picks `photos/cat-07.jpg` is saying where their photos are, not asking to
 * process one file — and a field left holding a file path fails later, in the backend,
 * with an error that points at the wrong thing.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FolderField } from './FolderField';

const dialog = vi.hoisted(() => ({
  hasNativeDialog: vi.fn(() => true),
  pickFolder: vi.fn(async () => '/Users/you/photos'),
  pickImageFile: vi.fn(async () => '/Users/you/photos/cat-07.jpg'),
}));

vi.mock('../lib/dialog', () => dialog);
vi.mock('../hooks/useFileDrop', () => ({
  useFileDrop: () => ({ dropping: false, available: true }),
}));

beforeEach(() => {
  dialog.hasNativeDialog.mockReturnValue(true);
});

function renderField() {
  const onChange = vi.fn();
  render(<FolderField id="folder" value="" onChange={onChange} />);
  return { onChange, user: userEvent.setup() };
}

describe('the pickers', () => {
  it('offers both an image and a folder button', async () => {
    // The Dataset Generator had neither — a bare text box beside two tabs that had them.
    renderField();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Image…' })).toBeEnabled());
    expect(screen.getByRole('button', { name: 'Folder…' })).toBeInTheDocument();
  });

  it('turns a picked image into the folder that holds it', async () => {
    const { onChange, user } = renderField();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Image…' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Image…' }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('/Users/you/photos'));
  });

  it('passes a picked folder straight through', async () => {
    const { onChange, user } = renderField();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Folder…' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Folder…' }));
    await waitFor(() => expect(onChange).toHaveBeenCalledWith('/Users/you/photos'));
  });

  it('reports nothing when the dialog is dismissed', async () => {
    // Cancelling must leave the field as it was, not blank it.
    // `pickFolder` resolves `string | null`; the mock's inferred type is narrower.
    dialog.pickFolder.mockResolvedValueOnce(null as unknown as string);
    const { onChange, user } = renderField();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Folder…' })).toBeEnabled());
    await user.click(screen.getByRole('button', { name: 'Folder…' }));
    await waitFor(() => expect(dialog.pickFolder).toHaveBeenCalled());
    expect(onChange).not.toHaveBeenCalled();
  });

  it('hides both buttons in a browser, leaving the field typable', async () => {
    // Wave 9's `web` mode has no native dialog. A disabled field with no picker would
    // leave no way in at all.
    dialog.hasNativeDialog.mockReturnValue(false);
    render(<FolderField id="folder" value="" onChange={vi.fn()} />);
    await waitFor(() =>
      expect(screen.queryByRole('button', { name: 'Image…' })).not.toBeInTheDocument(),
    );
    expect(screen.getByLabelText(/Image folder/)).toBeEnabled();
  });
});

describe('typing', () => {
  it('still reports what was typed', async () => {
    const { onChange, user } = renderField();
    await user.type(screen.getByLabelText(/Image folder/), '/');
    expect(onChange).toHaveBeenCalledWith('/');
  });

  it('says that an image is enough', async () => {
    renderField();
    expect(screen.getByText(/Pick an image and its folder is used/)).toBeInTheDocument();
  });
});

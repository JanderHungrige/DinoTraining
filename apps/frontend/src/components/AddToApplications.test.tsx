import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { storageKeyFor } from '../lib/persisted';

const invoke = vi.hoisted(() => vi.fn<(command: string) => Promise<unknown>>());
vi.mock('@tauri-apps/api/core', () => ({ invoke }));

import { AddToApplications } from './AddToApplications';

const FOLDER = '/Users/jan/Applications/DinoTraining.app';

beforeEach(() => {
  Object.defineProperty(window, '__TAURI_INTERNALS__', { value: {}, configurable: true });
});
afterEach(() => {
  delete (window as unknown as Record<string, unknown>)['__TAURI_INTERNALS__'];
  invoke.mockReset();
});

async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe('AddToApplications (doc 130)', () => {
  it('asks when the shell offers, and adds on request', async () => {
    invoke.mockImplementation((command) => Promise.resolve(command === 'applications_offer' ? FOLDER : FOLDER));
    render(<AddToApplications />);
    await flush();
    expect(screen.getByText('Add DinoTraining to your Applications folder?')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Add' }));
    await flush();
    expect(invoke).toHaveBeenLastCalledWith('add_to_applications');
    expect(screen.getByText(`Added: ${FOLDER}`)).toBeInTheDocument();
  });

  it('says nothing when there is nothing to offer (not a Homebrew install)', async () => {
    invoke.mockResolvedValue(null);
    const { container } = render(<AddToApplications />);
    await flush();
    expect(container).toBeEmptyDOMElement();
  });

  it('"Not now" is remembered: the shell is not even asked next time', async () => {
    invoke.mockResolvedValue(FOLDER);
    const { unmount } = render(<AddToApplications />);
    await flush();
    fireEvent.click(screen.getByRole('button', { name: 'Not now' }));
    expect(localStorage.getItem(storageKeyFor('addToApplications.dismissed'))).toBe('true');
    unmount();
    invoke.mockClear();
    render(<AddToApplications />);
    await flush();
    expect(invoke).not.toHaveBeenCalled();
  });

  it('outside the desktop shell it does nothing', async () => {
    delete (window as unknown as Record<string, unknown>)['__TAURI_INTERNALS__'];
    const { container } = render(<AddToApplications />);
    await flush();
    expect(container).toBeEmptyDOMElement();
    expect(invoke).not.toHaveBeenCalled();
  });
});

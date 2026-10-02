import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderInGerman } from '../i18n/testing';
import { storageKeyFor } from '../lib/persisted';

const invoke = vi.hoisted(() => vi.fn());
vi.mock('@tauri-apps/api/core', () => ({ invoke }));

import { UpdateNotice, type Update } from './UpdateNotice';

const UPDATE: Update = {
  current: '0.1.2',
  latest: '0.1.3',
  notes: 'https://github.com/JanderHungrige/DinoTraining/releases/tag/v0.1.3',
  download: 'https://dino.w3rth.de',
};

function inShell(on: boolean): void {
  if (on) Object.defineProperty(window, '__TAURI_INTERNALS__', { value: {}, configurable: true });
  else delete (window as unknown as Record<string, unknown>)['__TAURI_INTERNALS__'];
}

beforeEach(() => {
  invoke.mockReset();
  window.localStorage.clear();
  inShell(true);
});
afterEach(() => inShell(false));

describe('UpdateNotice (doc 158)', () => {
  it('says which version is out, with the download page and the notes', async () => {
    invoke.mockResolvedValue(UPDATE);
    render(<UpdateNotice />);
    expect(await screen.findByText('V-Rex 0.1.3 is available. You have 0.1.2.')).toBeInTheDocument();
    expect(invoke).toHaveBeenCalledWith('check_for_update');
    expect(screen.getByRole('link', { name: 'Get it' })).toHaveAttribute('href', 'https://dino.w3rth.de');
    expect(screen.getByRole('link', { name: 'What’s new' })).toHaveAttribute('href', UPDATE.notes);
  });

  it('remembers "Later" for that version only', async () => {
    invoke.mockResolvedValue(UPDATE);
    const first = render(<UpdateNotice />);
    fireEvent.click(await screen.findByRole('button', { name: 'Later' }));
    expect(screen.queryByRole('status')).toBeNull();
    expect(window.localStorage.getItem(storageKeyFor('update.dismissedVersion'))).toBe('"0.1.3"');
    first.unmount();

    render(<UpdateNotice />);
    await waitFor(() => expect(invoke).toHaveBeenCalledTimes(2));
    expect(screen.queryByRole('status')).toBeNull();

    invoke.mockResolvedValue({ ...UPDATE, latest: '0.1.4' });
    renderInGerman(<UpdateNotice />);
    expect(await screen.findByText('V-Rex 0.1.4 ist da. Du hast 0.1.2.')).toBeInTheDocument();
  });

  it('shows nothing when the shell has no update, fails, or is absent', async () => {
    invoke.mockResolvedValueOnce(null);
    const quiet = render(<UpdateNotice />);
    await waitFor(() => expect(invoke).toHaveBeenCalledTimes(1));
    expect(screen.queryByRole('status')).toBeNull();
    quiet.unmount();

    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    invoke.mockRejectedValueOnce(new Error('offline'));
    const failed = render(<UpdateNotice />);
    await waitFor(() => expect(warn).toHaveBeenCalled());
    expect(screen.queryByRole('status')).toBeNull();
    warn.mockRestore();
    failed.unmount();

    inShell(false);
    render(<UpdateNotice />);
    expect(invoke).toHaveBeenCalledTimes(2);
    expect(screen.queryByRole('status')).toBeNull();
  });
});

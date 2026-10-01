import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { renderInGerman } from '../i18n/testing';

const invoke = vi.hoisted(() => vi.fn<(command: string, args?: unknown) => Promise<unknown>>());
vi.mock('@tauri-apps/api/core', () => ({ invoke }));

import { ErrorActions } from './ErrorActions';

async function flush(): Promise<void> {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

beforeEach(() => {
  Object.defineProperty(window, '__TAURI_INTERNALS__', { value: {}, configurable: true });
});
afterEach(() => {
  delete (window as unknown as Record<string, unknown>)['__TAURI_INTERNALS__'];
  invoke.mockReset();
});

describe('ErrorActions (doc 140)', () => {
  it('opens the backend log', async () => {
    invoke.mockResolvedValue('/logs/backend.log');
    render(<ErrorActions message="backend exited during startup" />);
    fireEvent.click(screen.getByRole('button', { name: 'Open the log' }));
    await flush();
    expect(invoke).toHaveBeenCalledWith('open_backend_log', undefined);
  });

  it('says why when there is no log yet', async () => {
    invoke.mockRejectedValue('No log yet at C:\\logs\\backend.log');
    render(<ErrorActions message="failed" />);
    fireEvent.click(screen.getByRole('button', { name: 'Open the log' }));
    await flush();
    expect(screen.getByText(/No log yet/)).toBeInTheDocument();
  });

  it('reports the issue with the very error shown', async () => {
    invoke.mockResolvedValue(undefined);
    render(<ErrorActions message="backend exited during startup (exit code: 1)" />);
    fireEvent.click(screen.getByRole('button', { name: 'Report an issue' }));
    await flush();
    expect(invoke).toHaveBeenCalledWith('report_issue', { message: 'backend exited during startup (exit code: 1)' });
  });

  it('is absent outside the desktop app (nothing to open there)', () => {
    delete (window as unknown as Record<string, unknown>)['__TAURI_INTERNALS__'];
    const { container } = render(<ErrorActions message="x" />);
    expect(container).toBeEmptyDOMElement();
  });

  it('speaks German', () => {
    renderInGerman(<ErrorActions message="x" />);
    expect(screen.getByRole('button', { name: 'Log öffnen' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Problem melden' })).toBeInTheDocument();
  });
});

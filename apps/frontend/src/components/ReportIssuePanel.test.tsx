/** Doc 171: reporting an issue without an error, from Settings. */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

const invoke = vi.fn(() => Promise.resolve());
vi.mock('@tauri-apps/api/core', () => ({ invoke }));
const shell = vi.hoisted(() => ({ inside: false }));
vi.mock('../setup/shell', () => ({ inShell: () => shell.inside }));

import { NEW_ISSUE, ReportIssuePanel } from './ReportIssuePanel';

afterEach(() => {
  invoke.mockClear();
  shell.inside = false;
});

describe('ReportIssuePanel', () => {
  it('in the desktop app, opens the prefilled issue with no error message', async () => {
    shell.inside = true;
    render(<ReportIssuePanel />);
    fireEvent.click(screen.getByRole('button', { name: 'Report an issue or suggest an idea' }));
    await waitFor(() => expect(invoke).toHaveBeenCalledWith('report_issue', { message: '' }));
  });

  it('outside it, links to the new-issue page', () => {
    render(<ReportIssuePanel />);
    expect(screen.getByRole('link', { name: 'Report an issue or suggest an idea' })).toHaveAttribute('href', NEW_ISSUE);
    expect(invoke).not.toHaveBeenCalled();
  });
});

/**
 * The MCP connection panel (doc 64).
 *
 * One setup command and one warning carry this whole panel. The command has to be right
 * and copyable, because a wrong URL is the single most likely failure. The warning has to
 * be readable, because it is what makes "no authentication" a defensible choice rather
 * than an oversight.
 *
 * The tool list is fetched rather than written into the component, so the test that
 * matters is that it renders what the server said — not that it renders a list.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as mcpInfo from '../api/mcpInfo';
import { McpPanel } from './McpPanel';

vi.mock('../api/mcpInfo');

const INFO: mcpInfo.McpInfo = {
  url: 'http://127.0.0.1:8756/mcp',
  command: 'claude mcp add --transport http dinotraining http://127.0.0.1:8756/mcp',
  tools: [
    { name: 'list_datasets', summary: 'List datasets, with per-dataset counts.' },
    { name: 'finetune_model', summary: 'Fine-tune a whole detector on your classes.' },
  ],
};

beforeEach(() => {
  vi.mocked(mcpInfo.fetchMcpInfo).mockResolvedValue(INFO);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function stubClipboard(writeText: ReturnType<typeof vi.fn>): void {
  // jsdom's clipboard is getter-only, and this must run *after* `userEvent.setup()`,
  // which installs a stub of its own that would otherwise replace it.
  Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true });
}

async function renderPanel() {
  render(<McpPanel />);
  await screen.findByText(INFO.command);
}

describe('the setup command', () => {
  it('comes from the server rather than being written into the page', async () => {
    // A hardcoded URL is wrong the moment DINO_API_PORT is set, and the failure is a
    // client that silently connects to nothing.
    await renderPanel();

    expect(mcpInfo.fetchMcpInfo).toHaveBeenCalled();
    expect(screen.getByText(INFO.command)).toBeInTheDocument();
  });

  it('can be copied', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    await renderPanel();
    stubClipboard(writeText);

    await user.click(screen.getByRole('button', { name: /Copy the command/ }));

    expect(writeText).toHaveBeenCalledWith(INFO.command);
  });

  it('confirms the copy, so nobody pastes an empty clipboard', async () => {
    const user = userEvent.setup();
    await renderPanel();
    stubClipboard(vi.fn().mockResolvedValue(undefined));

    await user.click(screen.getByRole('button', { name: /Copy the command/ }));

    expect(await screen.findByRole('button', { name: 'Copied' })).toBeInTheDocument();
  });

  it('says so when the clipboard is refused, rather than appearing to work', async () => {
    // A packaged webview can refuse it. The command is on screen either way, so the
    // honest failure costs nothing and a silent one costs a confused user.
    const user = userEvent.setup();
    await renderPanel();
    stubClipboard(vi.fn().mockRejectedValue(new Error('denied')));

    await user.click(screen.getByRole('button', { name: /Copy the command/ }));

    expect(await screen.findByText(/copy the command above by hand/i)).toBeInTheDocument();
  });
});

describe('the tools it lists', () => {
  it('renders what the server reported', async () => {
    await renderPanel();

    expect(screen.getByText('list_datasets')).toBeInTheDocument();
    expect(screen.getByText('finetune_model')).toBeInTheDocument();
  });

  it('counts them rather than claiming a number', async () => {
    // The heading says "The 2 tools it gets" from the fetched list, so adding a tool
    // needs no edit here and cannot leave the count stale.
    await renderPanel();

    expect(screen.getByRole('heading', { name: /2 tools/ })).toBeInTheDocument();
  });
});

describe('what it warns about', () => {
  it('says the server is reachable only from this machine', async () => {
    // The one thing on this tab a user must not skim: it is what makes shipping an
    // unauthenticated tool server a defensible choice.
    await renderPanel();

    expect(screen.getByText(/only works on this machine/i)).toBeInTheDocument();
  });

  it('says there is no authentication', async () => {
    await renderPanel();

    expect(screen.getByText(/no authentication/i)).toBeInTheDocument();
  });
});

describe('when the backend cannot be reached', () => {
  it('shows the real reason rather than a generic failure', async () => {
    // The API writes its errors for a person — "Backend is not running" tells someone
    // what to do, and "Could not read the MCP details" does not.
    vi.mocked(mcpInfo.fetchMcpInfo).mockRejectedValue(new Error('Backend is not running.'));

    render(<McpPanel />);

    await waitFor(() =>
      expect(screen.getByText(/Backend is not running/)).toBeInTheDocument(),
    );
  });

  it('falls back to its own wording when the cause is not an Error', async () => {
    vi.mocked(mcpInfo.fetchMcpInfo).mockRejectedValue('something odd');

    render(<McpPanel />);

    await waitFor(() =>
      expect(screen.getByText(/Could not read the MCP details/)).toBeInTheDocument(),
    );
  });
});

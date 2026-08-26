/**
 * The Connection tab (docs 63 and 64).
 *
 * Two ways to let an assistant drive the app, and the tab's job is that both are found.
 * **MCP is the default** because it is the better one — typed tools beat a document the
 * model has to interpret — and the manual document is a click away rather than buried,
 * which is the mistake that hid fine-tuning for three waves.
 *
 * The manual half's own tests are about the handing over: the document is fetched from the
 * running backend rather than bundled, copying leads, and a webview that refuses the
 * clipboard says so instead of pretending.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as agentGuide from '../api/agentGuide';
import * as mcpInfo from '../api/mcpInfo';
import { ApiTab } from './ApiTab';

vi.mock('../api/agentGuide', async (original) => ({
  ...(await original<typeof agentGuide>()),
  fetchAgentGuide: vi.fn(),
}));
vi.mock('../api/mcpInfo');

const GUIDE = '# DinoTraining API\n\nCall `GET /models` first.\n\n## 1. Install a model\n';

beforeEach(() => {
  vi.mocked(agentGuide.fetchAgentGuide).mockResolvedValue(GUIDE);
  vi.mocked(mcpInfo.fetchMcpInfo).mockResolvedValue({
    url: 'http://127.0.0.1:8756/mcp',
    command: 'claude mcp add --transport http dinotraining http://127.0.0.1:8756/mcp',
    tools: [{ name: 'list_datasets', summary: 'List datasets.' }],
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

/**
 * jsdom's `navigator.clipboard` is getter-only, so it has to be redefined — and this must
 * run **after** `userEvent.setup()`, which installs a clipboard stub of its own and would
 * otherwise replace this one.
 */
function stubClipboard(writeText: ReturnType<typeof vi.fn>): void {
  Object.defineProperty(navigator, 'clipboard', {
    value: { writeText },
    configurable: true,
  });
}

/** Render and switch to the manual document, which is no longer the default mode. */
async function renderTab() {
  render(<ApiTab />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole('radio', { name: /Any assistant/ }));
  await waitFor(() => expect(screen.getByRole('heading', { name: /Install a model/ })).toBeInTheDocument());
  return userEvent.setup();
}

describe('where the document comes from', () => {
  it('fetches it rather than shipping a copy', async () => {
    // The endpoint reference is generated from the running backend's schema, so a copy
    // bundled at build time would describe whatever the API looked like then.
    await renderTab();

    expect(agentGuide.fetchAgentGuide).toHaveBeenCalled();
  });

  it('renders it as a document, not as a wall of markdown', async () => {
    await renderTab();

    // Real headings, because this markup is also the print source and a PDF's outline
    // comes from them.
    expect(screen.getByRole('heading', { name: 'DinoTraining API' })).toBeInTheDocument();
  });

  it('says so when the backend cannot be reached', async () => {
    // Rendered by hand rather than through `renderTab`, which waits for a heading that
    // never arrives when the fetch fails.
    vi.mocked(agentGuide.fetchAgentGuide).mockRejectedValue(new Error('Backend is not running.'));
    render(<ApiTab />);
    await userEvent.setup().click(await screen.findByRole('radio', { name: /Any assistant/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/not running/);
  });
});

describe('handing it over', () => {
  it('leads with copying, because that is what the feature is for', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const user = await renderTab();
    stubClipboard(writeText);

    await user.click(screen.getByRole('button', { name: /Copy for your AI/ }));

    expect(writeText).toHaveBeenCalledWith(GUIDE);
  });

  it('confirms the copy, so nobody pastes an empty clipboard', async () => {
    const user = await renderTab();
    stubClipboard(vi.fn().mockResolvedValue(undefined));

    await user.click(screen.getByRole('button', { name: /Copy for your AI/ }));

    expect(await screen.findByRole('button', { name: /Copied/ })).toBeInTheDocument();
  });

  it('admits a refused clipboard and points at the download', async () => {
    // A webview can refuse it. A button that appears to work is worse than one that says
    // it did not, because the failure surfaces as an empty paste much later.
    const user = await renderTab();
    stubClipboard(vi.fn().mockRejectedValue(new Error('no')));

    await user.click(screen.getByRole('button', { name: /Copy for your AI/ }));

    expect(await screen.findByRole('button', { name: /use Download/ })).toBeInTheDocument();
  });

  it('offers all three formats', async () => {
    await renderTab();

    expect(screen.getByRole('button', { name: /Copy for your AI/ })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Download .md' })).toBeEnabled();
    expect(screen.getByRole('button', { name: 'Save as PDF' })).toBeEnabled();
  });

  it('prints for the PDF rather than generating one on the backend', async () => {
    // The browser already has a PDF writer. Adding weasyprint to a 636 MB sidecar to
    // reproduce it would be the wrong trade (doc 56).
    const print = vi.fn();
    Object.assign(window, { print });
    const user = await renderTab();

    await user.click(screen.getByRole('button', { name: 'Save as PDF' }));

    expect(print).toHaveBeenCalled();
  });

  it('says which format an assistant actually wants', async () => {
    // PDF was asked for and is the worst of the three for the stated purpose. Saying so
    // costs a sentence and saves someone pasting a PDF into a chat box.
    await renderTab();

    expect(screen.getByText(/Markdown is what these models read best/)).toBeInTheDocument();
  });
});

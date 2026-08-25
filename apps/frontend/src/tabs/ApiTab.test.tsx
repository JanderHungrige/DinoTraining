/**
 * The API tab (doc 63).
 *
 * The feature is "hand this to your AI", so the tests are about the handing over: the
 * document is fetched from the running backend rather than bundled, copying is the primary
 * action, and a webview that refuses the clipboard says so instead of pretending.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as agentGuide from '../api/agentGuide';
import { ApiTab } from './ApiTab';

vi.mock('../api/agentGuide', async (original) => ({
  ...(await original<typeof agentGuide>()),
  fetchAgentGuide: vi.fn(),
}));

const GUIDE = '# DinoTraining API\n\nCall `GET /models` first.\n\n## 1. Install a model\n';

beforeEach(() => {
  vi.mocked(agentGuide.fetchAgentGuide).mockResolvedValue(GUIDE);
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

async function renderTab() {
  render(<ApiTab />);
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
    vi.mocked(agentGuide.fetchAgentGuide).mockRejectedValue(new Error('Backend is not running.'));
    render(<ApiTab />);

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

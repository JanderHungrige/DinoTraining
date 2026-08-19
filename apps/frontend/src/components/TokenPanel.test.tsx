import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TokenPanel } from './TokenPanel';

vi.mock('../api/settings', () => ({
  fetchTokenStatus: vi.fn(),
  fetchLicenceNotices: vi.fn(),
  saveToken: vi.fn(),
  clearToken: vi.fn(),
  acceptLicence: vi.fn(),
}));

const api = await import('../api/settings');

const NOT_CONFIGURED = {
  configured: false,
  hint: null,
  env_file: '/Users/x/DinoTraining/.env',
  accepted_licences: [],
};

const CONFIGURED = {
  configured: true,
  hint: '••••f123',
  env_file: '/Users/x/DinoTraining/.env',
  accepted_licences: ['sam3'],
};

const SAM3_NOTICE = {
  model_id: 'sam3',
  licence: 'SAM License (Meta, custom)',
  licence_url: 'https://huggingface.co/facebook/sam3',
  requires_access_request: true,
  accepted: false,
  explanation: 'This app never downloads it for you. Request access on the model page.',
};

beforeEach(() => {
  vi.mocked(api.fetchTokenStatus).mockResolvedValue(NOT_CONFIGURED);
  vi.mocked(api.fetchLicenceNotices).mockResolvedValue([SAM3_NOTICE]);
  vi.mocked(api.saveToken).mockResolvedValue(CONFIGURED);
  vi.mocked(api.clearToken).mockResolvedValue(NOT_CONFIGURED);
  vi.mocked(api.acceptLicence).mockResolvedValue(CONFIGURED);
});

afterEach(() => {
  vi.clearAllMocks();
});

describe('TokenPanel', () => {
  it('says the open path needs none of this', async () => {
    render(<TokenPanel />);
    expect(await screen.findByText(/Grounded SAM/)).toBeInTheDocument();
  });

  it('reports when no token is configured', async () => {
    render(<TokenPanel />);
    expect(await screen.findByText(/Not set/)).toBeInTheDocument();
  });

  it('keeps the save button disabled until something is typed', async () => {
    render(<TokenPanel />);
    const save = await screen.findByRole('button', { name: /save token/i });
    expect(save).toBeDisabled();
  });

  it('enables saving once a token is entered', async () => {
    const user = userEvent.setup();
    render(<TokenPanel />);
    await screen.findByRole('button', { name: /save token/i });

    await user.type(screen.getByLabelText(/access token/i), 'hf_secret_value_1234');
    expect(screen.getByRole('button', { name: /save token/i })).toBeEnabled();
  });

  it('sends the token and clears the field afterwards', async () => {
    const user = userEvent.setup();
    render(<TokenPanel />);
    await screen.findByRole('button', { name: /save token/i });

    const field = screen.getByLabelText(/access token/i);
    await user.type(field, 'hf_secret_value_1234');
    await user.click(screen.getByRole('button', { name: /save token/i }));

    await waitFor(() => expect(api.saveToken).toHaveBeenCalledWith('hf_secret_value_1234'));
    // The typed value must not linger in the DOM once it has been stored.
    await waitFor(() => expect((field as HTMLInputElement).value).toBe(''));
  });

  it('never renders the token itself, only the masked hint', async () => {
    vi.mocked(api.fetchTokenStatus).mockResolvedValue(CONFIGURED);
    const { container } = render(<TokenPanel />);

    await screen.findByText(/Configured/);
    expect(container.textContent).toContain('••••f123');
    expect(container.textContent).not.toContain('hf_');
  });

  it('masks the input so a shoulder-surfer cannot read it', async () => {
    render(<TokenPanel />);
    const field = await screen.findByLabelText(/access token/i);
    expect(field).toHaveAttribute('type', 'password');
  });

  it('shows where the file lives so it can be edited by hand', async () => {
    render(<TokenPanel />);
    expect(await screen.findByText('/Users/x/DinoTraining/.env')).toBeInTheDocument();
  });

  it('flags a model that needs manual approval', async () => {
    render(<TokenPanel />);
    expect(await screen.findByText(/manual approval/i)).toBeInTheDocument();
  });

  it('shows the backend explanation rather than its own wording', async () => {
    render(<TokenPanel />);
    expect(await screen.findByText(/never downloads it for you/i)).toBeInTheDocument();
  });

  it('links to the model page where access is actually requested', async () => {
    render(<TokenPanel />);
    const link = await screen.findByRole('link', { name: /open the model page/i });
    expect(link).toHaveAttribute('href', 'https://huggingface.co/facebook/sam3');
  });

  it('records a licence acknowledgement', async () => {
    const user = userEvent.setup();
    render(<TokenPanel />);
    await user.click(await screen.findByRole('checkbox'));
    await waitFor(() => expect(api.acceptLicence).toHaveBeenCalledWith('sam3'));
  });

  it('does not offer to remove a token that is not there', async () => {
    render(<TokenPanel />);
    await screen.findByText(/Not set/);
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument();
  });

  it('offers removal once one is stored', async () => {
    vi.mocked(api.fetchTokenStatus).mockResolvedValue(CONFIGURED);
    render(<TokenPanel />);
    expect(await screen.findByRole('button', { name: /remove/i })).toBeInTheDocument();
  });

  it('surfaces a save failure instead of silently doing nothing', async () => {
    const user = userEvent.setup();
    vi.mocked(api.saveToken).mockRejectedValue(new Error('That is not a valid token.'));
    render(<TokenPanel />);
    await screen.findByRole('button', { name: /save token/i });

    await user.type(screen.getByLabelText(/access token/i), 'nope');
    await user.click(screen.getByRole('button', { name: /save token/i }));

    expect(await screen.findByText(/not a valid token/i)).toBeInTheDocument();
  });
});

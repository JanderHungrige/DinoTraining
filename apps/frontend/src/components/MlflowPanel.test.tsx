import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { MlflowPanel } from './MlflowPanel';

const OFF = { configured: false, uri: null, experiment: 'V-Rex', register_models: true, auth: 'none' as const, username: null };
const ON = { ...OFF, configured: true, uri: 'http://127.0.0.1:5055', auth: 'basic' as const, username: 'jan' };

vi.mock('../api/mlops', () => ({
  getMlflowStatus: vi.fn(),
  saveMlflowSettings: vi.fn(),
  clearMlflowSettings: vi.fn(),
  testMlflow: vi.fn(),
}));
const api = await import('../api/mlops');

beforeEach(() => vi.clearAllMocks());

describe('MlflowPanel (doc 123)', () => {
  it('saves the URI and credentials, then shows only which kind is set', async () => {
    const user = userEvent.setup();
    vi.mocked(api.getMlflowStatus).mockResolvedValue(OFF);
    vi.mocked(api.saveMlflowSettings).mockResolvedValue(ON);
    render(<MlflowPanel />);
    expect(await screen.findByText('Off: runs are not sent anywhere.')).toBeInTheDocument();
    await user.type(screen.getByLabelText('Tracking URI'), 'http://127.0.0.1:5055');
    await user.click(screen.getByText('Credentials (if your server needs them)'));
    await user.type(screen.getByLabelText('User'), 'jan');
    await user.type(screen.getByLabelText('Password'), 'pw');
    await user.click(screen.getByRole('button', { name: 'Save' }));
    expect(api.saveMlflowSettings).toHaveBeenCalledWith({
      uri: 'http://127.0.0.1:5055', experiment: 'V-Rex', register_models: true, username: 'jan', password: 'pw',
    });
    expect(await screen.findByText(/On: http:\/\/127.0.0.1:5055/)).toHaveTextContent('user and password set');
    expect(screen.getByLabelText('Password')).toHaveValue('');
  });

  it('says what the connection test found', async () => {
    const user = userEvent.setup();
    vi.mocked(api.getMlflowStatus).mockResolvedValue(ON);
    vi.mocked(api.testMlflow).mockResolvedValue({ ok: false, message: 'MLflow at http://127.0.0.1:5055 is not reachable: refused' });
    render(<MlflowPanel />);
    await user.click(await screen.findByRole('button', { name: 'Test connection' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('not reachable');
  });
});

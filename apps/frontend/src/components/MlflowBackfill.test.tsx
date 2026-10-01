import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { MlflowBackfill } from './MlflowBackfill';

vi.mock('../api/mlops', () => ({ startBackfill: vi.fn(), getBackfill: vi.fn() }));
const api = await import('../api/mlops');

const job = (state: 'running' | 'complete', sent: number) => ({
  job_id: 'b1', state, total: 28, sent, skipped: 3, failed: 0, notes: [],
});

describe('MlflowBackfill (doc 124)', () => {
  it('sends, shows the progress, and says when it is done', async () => {
    const user = userEvent.setup();
    vi.mocked(api.startBackfill).mockResolvedValue(job('running', 0));
    vi.mocked(api.getBackfill).mockResolvedValue(job('complete', 25));
    render(<MlflowBackfill enabled />);
    await user.click(screen.getByRole('button', { name: 'Send existing models to MLflow' }));
    // The first poll comes after POLL_MS (1 s), which is exactly findBy's default wait.
    expect(
      await screen.findByText('25 of 28 sent, 3 already there or not trained here, 0 failed. Done.', {}, { timeout: 3000 }),
    ).toBeInTheDocument();
  });

  it('is off until MLflow is set up', () => {
    render(<MlflowBackfill enabled={false} />);
    expect(screen.getByRole('button', { name: 'Send existing models to MLflow' })).toBeDisabled();
  });
});

import { render, screen } from '@testing-library/react';
import { StrictMode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../api/client';
import { PrepareTab } from './PrepareTab';

vi.mock('../api/datasets', async () => {
  const actual = await vi.importActual<typeof import('../api/datasets')>('../api/datasets');
  return { ...actual, listDatasets: vi.fn() };
});
vi.mock('../api/prep', async () => {
  const actual = await vi.importActual<typeof import('../api/prep')>('../api/prep');
  return {
    ...actual,
    listTargets: vi.fn(),
    getLastAudit: vi.fn(async () => null),
    getPrepState: vi.fn(async () => ({ excluded: [], class_map: {} })),
    getSplit: vi.fn(async () => null),
  };
});
vi.mock('../api/prepPlan', async () => {
  const actual = await vi.importActual<typeof import('../api/prepPlan')>('../api/prepPlan');
  return {
    ...actual,
    listRecipes: vi.fn(async () => []),
    getBalance: vi.fn(() => new Promise(() => undefined)),
    getAugmentation: vi.fn(() => new Promise(() => undefined)),
  };
});

const datasets = await import('../api/datasets');
const prep = await import('../api/prep');

beforeEach(() => {
  localStorage.clear();
  // As `apiFetch` does: an aborted request rejects as "cannot reach the backend".
  vi.mocked(datasets.listDatasets).mockImplementation(
    (signal?: AbortSignal) =>
      new Promise((resolve, reject) => {
        signal?.addEventListener('abort', () => reject(new ApiError(0, 'unreachable', 'Cannot reach the DinoTraining backend')));
        setTimeout(() => resolve([{ id: 'd1', name: 'Blood cells', counts: { images: 3, masks: 0 } } as never]), 0);
      }),
  );
  vi.mocked(prep.listTargets).mockResolvedValue([
    { id: 'head-detection-dinov2', label: 'Detection head on DINOv2', task: 'detection', annotation_kind: 'boxes', input_size: 448, min_visible_px: 28 },
  ]);
});

describe('PrepareTab', () => {
  it('does not call a request it cancelled itself a failure (found live, StrictMode)', async () => {
    render(
      <StrictMode>
        <PrepareTab />
      </StrictMode>,
    );
    expect(await screen.findByRole('option', { name: 'Blood cells (3 pictures)' })).toBeInTheDocument();
    expect(screen.queryByText(/Cannot reach/)).not.toBeInTheDocument();
    // Nothing audited yet, so the flow opens on the audit.
    expect(screen.getByRole('button', { name: 'Run the audit' })).toBeEnabled();
  });
});

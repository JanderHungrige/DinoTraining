import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import * as datasets from '../api/datasets';
import { renderInGerman } from '../i18n/testing';
import { DatasetWhere } from './DatasetWhere';

vi.mock('../api/datasets', async () => {
  const actual = await vi.importActual<typeof import('../api/datasets')>('../api/datasets');
  return { ...actual, getDatasetFolder: vi.fn() };
});

const FOLDER = 'C:\\Users\\jan\\AppData\\Local\\DinoTraining\\data\\examples\\3_fire_site_3.4-rgb';

beforeEach(() => {
  vi.mocked(datasets.getDatasetFolder).mockReset().mockResolvedValue({ folder: FOLDER, exists: true, copies: true });
});

describe('DatasetWhere (2026-10-02)', () => {
  it('names the folder the backend reports and says how to open the dataset', async () => {
    render(<DatasetWhere datasetId="osdar" name="OSDaR23 · 3_fire_site_3.4" />);
    expect(await screen.findByText(`Its pictures are in ${FOLDER}.`)).toBeInTheDocument();
    expect(datasets.getDatasetFolder).toHaveBeenCalledWith('osdar', expect.any(AbortSignal));
    expect(screen.getByText(/Annotation Studio → “A dataset you already have” → “OSDaR23 · 3_fire_site_3\.4”/)).toBeInTheDocument();
  });

  it('still says how to open it when the folder is unknown, and speaks German', async () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    vi.mocked(datasets.getDatasetFolder).mockRejectedValue(new Error('offline'));
    renderInGerman(<DatasetWhere datasetId="osdar" name="Zellen" />);
    expect(await screen.findByText(/„Einem Datensatz, den du schon hast“ → „Zellen“/)).toBeInTheDocument();
    expect(screen.queryByText(/Die Bilder liegen in/)).toBeNull();
    warn.mockRestore();
  });
});

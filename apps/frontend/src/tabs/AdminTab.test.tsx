/**
 * The model catalogue's family sections.
 *
 * Reported twice, the second time as "can you add a download for RF-DETR, or did I just
 * miss it?" — and no, it was not there. RF-DETR and Depth Anything had catalogue entries,
 * licences, sizes and a working download route, and the Admin tab rendered neither, because
 * it kept a hand-written `FAMILY_ORDER` array that had never been updated. Nothing failed:
 * the array typechecked as a `ModelFamily[]` while being a *subset* of one, so two whole
 * families were unreachable and every layer reported success.
 *
 * The fix is that the order is derived from the labels, so a family that exists is a family
 * that renders. These tests hold that property rather than the current list — a seventh
 * family should need no edit here, and a test that named the six would pass while the
 * seventh was invisible, which is precisely the bug.
 */

import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { FAMILY_LABELS, type ModelFamily, type ModelInfo } from '../api/models';
import * as models from '../api/models';
import * as useModelsHook from '../hooks/useModels';
import * as useTrainerOptionsHook from '../hooks/useTrainerOptions';
import { AdminTab } from './AdminTab';

vi.mock('../hooks/useModels');
vi.mock('../hooks/useTrainerOptions');
vi.mock('../api/models', async (importOriginal) => ({
  ...(await importOriginal<typeof models>()),
  getAccelerator: vi.fn().mockResolvedValue(null),
}));
// Panels with fetches of their own; each is covered by its own file.
vi.mock('../components/HeadCatalogPanel', () => ({ HeadCatalogPanel: () => null }));
vi.mock('../components/AnnotatorReadiness', () => ({ AnnotatorReadiness: () => null }));
vi.mock('../components/TokenPanel', () => ({ TokenPanel: () => null }));
vi.mock('../components/GpuPanel', () => ({ GpuPanel: () => null }));

function model(id: string, family: ModelFamily): ModelInfo {
  return {
    id,
    repo_id: `org/${id}`,
    kind: 'detector',
    family,
    gated: false,
    approx_size_mb: 100,
    description: 'A model.',
    licence: 'Apache-2.0',
    licence_url: '',
    requires_access_request: false,
    non_commercial: false,
    installed: false,
    starter: false,
  } as ModelInfo;
}

/** One model per family — the case the old hand-written order got wrong. */
const EVERY_FAMILY: ModelInfo[] = (Object.keys(FAMILY_LABELS) as ModelFamily[]).map(
  (family) => model(`${family}-example`, family),
);

function mockModels(list: ModelInfo[]): void {
  vi.mocked(useModelsHook.useModels).mockReturnValue({
    models: list,
    system: null,
    jobs: {},
    loading: false,
    error: null,
    busy: {},
    download: vi.fn(),
    remove: vi.fn(),
  } as unknown as ReturnType<typeof useModelsHook.useModels>);
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useTrainerOptionsHook.useTrainerOptions).mockReturnValue({
    backbones: [],
    loading: false,
  } as unknown as ReturnType<typeof useTrainerOptionsHook.useTrainerOptions>);
  mockModels(EVERY_FAMILY);
});

describe('the family sections', () => {
  it('renders one for every family the catalogue has', () => {
    // The regression test. Written over the label map rather than a literal list, so a new
    // family is covered the moment it exists.
    render(<AdminTab />);

    for (const label of Object.values(FAMILY_LABELS)) {
      expect(screen.getByRole('heading', { name: label })).toBeInTheDocument();
    }
  });

  it('renders the RF-DETR section by name', () => {
    // Named explicitly because this is the one that was reported missing, twice.
    render(<AdminTab />);

    expect(screen.getByRole('heading', { name: /RF-DETR/ })).toBeInTheDocument();
    expect(screen.getByText('rf-detr-example')).toBeInTheDocument();
  });

  it('renders the Depth Anything section by name', () => {
    render(<AdminTab />);

    expect(screen.getByRole('heading', { name: /Depth Anything/ })).toBeInTheDocument();
    expect(screen.getByText('depth-anything-example')).toBeInTheDocument();
  });

  it('offers a download for a model in a newly-covered family', () => {
    // A heading with no way to install anything under it would be the same dead end in
    // nicer wording — the point is reaching the download.
    render(<AdminTab />);

    expect(screen.getAllByRole('button', { name: /^Download$/ }).length).toBe(
      EVERY_FAMILY.length,
    );
  });
});

describe('what it leaves out', () => {
  it('omits a family with no models rather than showing an empty heading', () => {
    mockModels([model('grounding-dino-tiny', 'grounding-dino')]);

    render(<AdminTab />);

    expect(screen.getByRole('heading', { name: FAMILY_LABELS['grounding-dino'] })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: FAMILY_LABELS['rf-detr'] })).not.toBeInTheDocument();
  });

  it('shows no sections at all while the catalogue is loading', () => {
    vi.mocked(useModelsHook.useModels).mockReturnValue({
      models: [],
      system: null,
      jobs: {},
      loading: true,
      error: null,
      busy: {},
      download: vi.fn(),
      remove: vi.fn(),
    } as unknown as ReturnType<typeof useModelsHook.useModels>);

    render(<AdminTab />);

    expect(screen.getByRole('status')).toHaveTextContent(/Loading model catalogue/);
    expect(screen.queryByRole('heading', { name: FAMILY_LABELS['rf-detr'] })).not.toBeInTheDocument();
  });
});

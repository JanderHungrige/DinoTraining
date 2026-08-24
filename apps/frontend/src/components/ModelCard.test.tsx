/**
 * What the admin panel says about a model *before* you download it (doc 35).
 *
 * The licence used to reach the screen only for gated models, through the token panel. So
 * an **ungated CC BY-NC** model — which is exactly the case where not knowing costs
 * something — displayed no licence at all. These tests are about the ungated path.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { ModelInfo } from '../api/models';
import { ModelCard } from './ModelCard';

function model(overrides: Partial<ModelInfo> = {}): ModelInfo {
  return {
    id: 'depth-anything-v2-small',
    repo_id: 'depth-anything/Depth-Anything-V2-Small-hf',
    kind: 'depth-estimator',
    family: 'depth-anything',
    gated: false,
    approx_size_mb: 95,
    description: 'Monocular depth estimation.',
    licence: 'Apache-2.0',
    licence_url: 'https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf',
    requires_access_request: false,
    non_commercial: false,
  redistribution: 'free' as const,
  redistribution_note: '',
    installed: false,
    size_on_disk_mb: 0,
    available: true,
    unavailable_reason: null,
    ...overrides,
  };
}

function renderCard(overrides: Partial<ModelInfo> = {}) {
  return render(
    <ModelCard
      model={model(overrides)}
      job={undefined}
      busy={false}
      onDownload={vi.fn()}
      onRemove={vi.fn()}
    />,
  );
}

describe('stating the licence', () => {
  it('shows the licence on an ungated model', () => {
    renderCard();
    expect(screen.getByText('Apache-2.0')).toBeInTheDocument();
  });

  it('links the licence to where it can be read', () => {
    renderCard();
    expect(screen.getByRole('link', { name: 'Apache-2.0' })).toHaveAttribute(
      'href',
      'https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf',
    );
  });

  it('states it before the download, not after', () => {
    // `installed: false` is the pre-download state; the licence must already be there.
    renderCard({ installed: false });
    expect(screen.getByText('Apache-2.0')).toBeInTheDocument();
    expect(screen.queryByText(/Installed/)).not.toBeInTheDocument();
  });

  it('keeps showing it once installed', () => {
    renderCard({ installed: true, size_on_disk_mb: 95 });
    expect(screen.getByText('Apache-2.0')).toBeInTheDocument();
  });
});

describe('flagging a non-commercial licence', () => {
  it('badges a model whose licence forbids commercial use', () => {
    renderCard({ licence: 'CC BY-NC 4.0', non_commercial: true });
    expect(screen.getByText('Non-commercial')).toBeInTheDocument();
  });

  it('does not badge a permissive one', () => {
    renderCard();
    expect(screen.queryByText('Non-commercial')).not.toBeInTheDocument();
  });

  it('reads the flag, never the licence text', () => {
    // The decisive test. A licence worded without "NC" that is still non-commercial must
    // badge; a permissive licence whose text happens to contain those letters must not.
    // Substring-matching the licence string gets both of these backwards.
    renderCard({ licence: 'Research Use Only (custom)', non_commercial: true });
    expect(screen.getByText('Non-commercial')).toBeInTheDocument();
  });

  it('does not badge a permissive licence whose text merely contains "nc"', () => {
    renderCard({ licence: 'Non-Commercial-Free Public Licence', non_commercial: false });
    expect(screen.queryByText('Non-commercial')).not.toBeInTheDocument();
  });

  it('names the licence in the badge tooltip, so the badge is not the whole story', () => {
    renderCard({ licence: 'CC BY-NC 4.0', non_commercial: true });
    expect(screen.getByText('Non-commercial')).toHaveAttribute(
      'title',
      'Licensed CC BY-NC 4.0',
    );
  });
});

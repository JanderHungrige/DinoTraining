/**
 * What must be dealt with before shipping (doc 54).
 *
 * The thing this component exists to prevent is a *category error*: concluding that a
 * copyleft model cannot be sold, when it can, and the real obligation is far larger than
 * deleting a file. So the tests check that three obligations read as three obligations.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { ModelInfo } from '../api/models';
import { DistributionNotice, restrictedInstalled } from './DistributionNotice';

function model(over: Partial<ModelInfo> = {}): ModelInfo {
  return {
    id: 'm1',
    repo_id: 'org/thing',
    kind: 'backbone',
    family: 'dinov2',
    gated: false,
    approx_size_mb: 100,
    description: '',
    licence: 'Apache-2.0',
    licence_url: 'https://example.test',
    requires_access_request: false,
    non_commercial: false,
    redistribution: 'free',
    redistribution_note: '',
    installed: true,
    unavailable_reason: null,
    ...over,
  } as unknown as ModelInfo;
}

const NC = model({
  id: 'depth-anything-v2-large',
  repo_id: 'depth-anything/Large',
  licence: 'CC BY-NC 4.0',
  non_commercial: true,
  redistribution: 'non-commercial',
  redistribution_note: 'Cannot be used or shipped commercially. Remove it before distributing a commercial build.',
});

const RESTRICTED = model({
  id: 'sam3',
  repo_id: 'facebook/sam3',
  licence: 'SAM License (Meta, custom)',
  redistribution: 'restricted',
  redistribution_note: "Ships under the vendor's own terms rather than a standard licence.",
});

const COPYLEFT = model({
  id: 'some-yolo',
  repo_id: 'org/yolo',
  licence: 'AGPL-3.0',
  redistribution: 'copyleft',
  redistribution_note:
    "Commercial use is allowed, but distributing it obliges releasing this whole app's source under the same licence.",
});

describe('when it appears at all', () => {
  it('says nothing when everything installed is permissive', () => {
    // A standing warning that never changes is one the user stops reading.
    const { container } = render(<DistributionNotice models={[model(), model({ id: 'm2' })]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('ignores a restricted model that is not installed', () => {
    // The constraint is a property of what was downloaded, not of the catalogue.
    const { container } = render(
      <DistributionNotice models={[{ ...NC, installed: false } as ModelInfo]} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('appears for an installed restricted model', () => {
    render(<DistributionNotice models={[model(), NC]} />);
    expect(screen.getByText(/Before you distribute/)).toBeInTheDocument();
  });

  it('counts only the restricted ones', () => {
    render(<DistributionNotice models={[model(), model({ id: 'm2' }), NC]} />);
    expect(screen.getByText(/1 installed model comes/)).toBeInTheDocument();
  });
});

describe('what it says about each obligation', () => {
  it('calls a non-commercial licence non-commercial', () => {
    render(<DistributionNotice models={[NC]} />);
    expect(screen.getByText(/Cannot be used or shipped commercially/)).toBeInTheDocument();
  });

  it('does not call a copyleft licence non-commercial', () => {
    // The correction this component was built for: AGPL permits selling. The obligation is
    // that shipping it makes the whole app AGPL — a decision, not a deletion.
    render(<DistributionNotice models={[COPYLEFT]} />);
    expect(screen.getByText(/Commercial use is allowed/)).toBeInTheDocument();
    expect(screen.queryByText(/Cannot be used or shipped commercially/)).not.toBeInTheDocument();
  });

  it('does not paraphrase a custom vendor licence', () => {
    render(<DistributionNotice models={[RESTRICTED]} />);
    expect(screen.getByText(/own terms rather than a standard licence/)).toBeInTheDocument();
  });

  it('shows the licence itself beside every entry', () => {
    render(<DistributionNotice models={[NC, RESTRICTED, COPYLEFT]} />);
    expect(screen.getByText('CC BY-NC 4.0')).toBeInTheDocument();
    expect(screen.getByText('SAM License (Meta, custom)')).toBeInTheDocument();
    expect(screen.getByText('AGPL-3.0')).toBeInTheDocument();
  });

  it('says removing the weights is the whole fix', () => {
    render(<DistributionNotice models={[NC]} />);
    expect(screen.getByText(/deletes its weights from the cache/)).toBeInTheDocument();
  });
});

describe('restrictedInstalled', () => {
  it('keeps installed non-free models only', () => {
    const models = [model(), NC, RESTRICTED, { ...COPYLEFT, installed: false } as ModelInfo];
    expect(restrictedInstalled(models).map((m) => m.id)).toEqual([
      'depth-anything-v2-large',
      'sam3',
    ]);
  });

  it('is empty for an empty catalogue', () => {
    expect(restrictedInstalled([])).toEqual([]);
  });
});

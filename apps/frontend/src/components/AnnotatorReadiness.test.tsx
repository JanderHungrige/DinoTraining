/**
 * Grounded SAM in Admin (doc 65).
 *
 * Reported as "Grounded SAM does not appear anything for the user to install", and it is
 * exactly right: it is not a model, it is two of them chained, and Admin listed those two
 * under their own names in two different family sections. Every other tab calls the thing
 * "Grounded SAM", so the one screen where you install it was the only screen that did not.
 *
 * So these tests are about the name and the parts: the pipeline appears by the name the
 * rest of the app uses, and it says which pieces are missing — because "Not installed"
 * with no list is the same dead end in nicer wording.
 */

import { render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import * as annotators from '../api/annotators';
import { AnnotatorReadiness } from './AnnotatorReadiness';

vi.mock('../api/annotators');

function part(id: string, over: Partial<annotators.RequiredModel> = {}): annotators.RequiredModel {
  return {
    id,
    name: id,
    installed: false,
    gated: false,
    approx_size_mb: 100,
    licence: 'Apache-2.0',
    licence_url: '',
    ...over,
  };
}

function annotator(over: Partial<annotators.AnnotatorInfo> = {}): annotators.AnnotatorInfo {
  return {
    id: 'grounded-sam',
    name: 'Grounded SAM',
    description: 'Grounding DINO finds it, SAM 2.1 outlines it.',
    licence: 'Apache-2.0',
    licence_url: '',
    gated: false,
    requires_access_request: false,
    prompt_style: 'phrases',
    approx_size_mb: 834,
    ready: false,
    missing_model_ids: ['grounding-dino-tiny', 'sam2.1-hiera-small'],
    models: [part('grounding-dino-tiny'), part('sam2.1-hiera-small')],
    ...over,
  };
}

beforeEach(() => {
  // Cleared, not just restored: the call *counts* are the assertion in "staying current",
  // and an auto-mocked module function carries its history across tests otherwise.
  vi.clearAllMocks();
  vi.mocked(annotators.listAnnotators).mockResolvedValue([annotator()]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('naming the pipeline', () => {
  it('shows it by the name the rest of the app uses', async () => {
    // The whole bug: the two parts were on screen, and the thing the user was looking for
    // was not.
    render(<AnnotatorReadiness />);

    expect(await screen.findByText('Grounded SAM')).toBeInTheDocument();
  });

  it('names both parts, so "not installed" says what to do about it', async () => {
    render(<AnnotatorReadiness />);

    expect(await screen.findByText('grounding-dino-tiny')).toBeInTheDocument();
    expect(screen.getByText('sam2.1-hiera-small')).toBeInTheDocument();
  });

  it('marks each part installed or not, rather than only the pipeline', async () => {
    // Half-installed is the confusing state: one download done, still "Not installed".
    vi.mocked(annotators.listAnnotators).mockResolvedValue([
      annotator({
        missing_model_ids: ['sam2.1-hiera-small'],
        models: [
          part('grounding-dino-tiny', { installed: true }),
          part('sam2.1-hiera-small'),
        ],
      }),
    ]);
    render(<AnnotatorReadiness />);

    expect(await screen.findByText(/Install sam2\.1-hiera-small above/)).toBeInTheDocument();
    expect(screen.queryByText(/Install grounding-dino-tiny/)).not.toBeInTheDocument();
  });
});

describe('readiness', () => {
  it('says Ready only when every part is there', async () => {
    vi.mocked(annotators.listAnnotators).mockResolvedValue([
      annotator({ ready: true, missing_model_ids: [], models: [part('a', { installed: true })] }),
    ]);
    render(<AnnotatorReadiness />);

    expect(await screen.findByText('Ready')).toBeInTheDocument();
  });

  it('takes readiness from the server rather than recomputing it', async () => {
    // The backend decides what a pipeline needs. A second opinion here is a second thing
    // to keep in sync, and it would disagree the first time a pipeline gains a part.
    vi.mocked(annotators.listAnnotators).mockResolvedValue([
      annotator({ ready: false, models: [part('a', { installed: true })] }),
    ]);
    render(<AnnotatorReadiness />);

    expect(await screen.findByText('Not installed')).toBeInTheDocument();
  });

  it('warns when a token is not enough', async () => {
    // SAM 3 needs an access request Meta approves by hand. Someone who pastes a token and
    // waits for a download that is never coming has been failed by this panel.
    vi.mocked(annotators.listAnnotators).mockResolvedValue([
      annotator({ id: 'sam3', name: 'SAM 3', requires_access_request: true }),
    ]);
    render(<AnnotatorReadiness />);

    expect(await screen.findByText(/requesting access on HuggingFace/)).toBeInTheDocument();
  });

  it('flags a gated part as needing a token', async () => {
    vi.mocked(annotators.listAnnotators).mockResolvedValue([
      annotator({ models: [part('sam3', { gated: true })] }),
    ]);
    render(<AnnotatorReadiness />);

    expect(await screen.findByText('needs your token')).toBeInTheDocument();
  });
});

describe('staying current', () => {
  it('re-reads when the parent says a download finished', async () => {
    // Otherwise installing both parts leaves the panel insisting they are missing until
    // the tab is reopened — which reads as the download having failed.
    const { rerender } = render(<AnnotatorReadiness refreshKey={0} />);
    await screen.findByText('Grounded SAM');

    rerender(<AnnotatorReadiness refreshKey={1} />);

    await waitFor(() => expect(annotators.listAnnotators).toHaveBeenCalledTimes(2));
  });

  it('does not re-read on an unrelated render', async () => {
    const { rerender } = render(<AnnotatorReadiness refreshKey={3} />);
    await screen.findByText('Grounded SAM');

    rerender(<AnnotatorReadiness refreshKey={3} />);

    expect(annotators.listAnnotators).toHaveBeenCalledTimes(1);
  });
});

describe('when the endpoint fails', () => {
  it('disappears instead of taking the model list down with it', async () => {
    // This panel is a convenience on a tab whose actual job is installing models. An
    // error boundary here would cost the user the thing they came for.
    vi.mocked(annotators.listAnnotators).mockRejectedValue(new Error('offline'));

    const { container } = render(<AnnotatorReadiness />);

    await waitFor(() => expect(container).toBeEmptyDOMElement());
  });
});

/**
 * Tests for the community import form.
 *
 * The first test is a regression from integration: options arrive asynchronously, and
 * seeding `useState` from `props[0]` leaves React's controlled value at "" while the
 * <select> happily renders its first option. The form looks filled in and the submit
 * button is disabled forever. No amount of shape-checking catches that — only
 * rendering with the empty-then-populated sequence a real load produces.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { BackboneInfo } from '../api/backbones';
import type { HeadTypeInfo } from '../api/heads';
import { HeadImportForm } from './HeadImportForm';

function backbone(id = 'dinov2-small'): BackboneInfo {
  return {
    id,
    family: 'dinov2',
    gated: false,
    installed: true,
    capabilities: {
      patch_size: 14,
      embed_dim: 384,
      num_prefix_tokens: 1,
      num_layers: 12,
      image_size: 518,
    },
  };
}

function headType(id = 'linear-classifier'): HeadTypeInfo {
  return {
    id,
    task: 'classification',
    title: 'Linear classifier',
    description: 'Linear probe.',
    trainable: true,
    target_format: 'image-labels',
    consumes: 'cls',
    geometry: 'center-crop',
    metrics: ['accuracy'],
    primary_metric: 'accuracy',
    primary_metric_mode: 'max',
    render_hint: 'labels',
    compatible: true,
    incompatible_reason: null,
  };
}

function renderForm(overrides: { headTypes?: HeadTypeInfo[]; backbones?: BackboneInfo[] } = {}) {
  const onImport = vi.fn().mockResolvedValue(true);
  const view = render(
    <HeadImportForm
      headTypes={overrides.headTypes ?? [headType()]}
      backbones={overrides.backbones ?? [backbone()]}
      busy={false}
      onImport={onImport}
    />,
  );
  return { onImport, view };
}

describe('HeadImportForm', () => {
  it('submits with the visible selections when options arrive after first render', async () => {
    const user = userEvent.setup();
    const onImport = vi.fn().mockResolvedValue(true);

    // Mount empty, exactly as the real load does before the fetches resolve.
    const { rerender } = render(
      <HeadImportForm headTypes={[]} backbones={[]} busy={false} onImport={onImport} />,
    );
    rerender(
      <HeadImportForm
        headTypes={[headType()]}
        backbones={[backbone()]}
        busy={false}
        onImport={onImport}
      />,
    );

    await user.type(screen.getByPlaceholderText('owner/name'), 'someone/probe');
    const submit = screen.getByRole('button', { name: 'Import head' });
    expect(submit).toBeEnabled();

    await user.click(submit);
    expect(onImport).toHaveBeenCalledWith({
      repo_id: 'someone/probe',
      head_type_id: 'linear-classifier',
      backbone_id: 'dinov2-small',
      num_classes: null,
    });
  });

  it('states the safetensors rule before the user can fail on it', () => {
    renderForm();
    expect(screen.getByText(/safetensors/)).toBeInTheDocument();
    expect(screen.getByText(/run arbitrary code/)).toBeInTheDocument();
  });

  it('keeps submit disabled until a repo id is entered', () => {
    renderForm();
    expect(screen.getByRole('button', { name: 'Import head' })).toBeDisabled();
  });

  it('trims the repo id before sending it', async () => {
    const user = userEvent.setup();
    const { onImport } = renderForm();

    await user.type(screen.getByPlaceholderText('owner/name'), '  someone/probe  ');
    await user.click(screen.getByRole('button', { name: 'Import head' }));

    expect(onImport).toHaveBeenCalledWith(
      expect.objectContaining({ repo_id: 'someone/probe' }),
    );
  });

  it('passes an explicit class count when given', async () => {
    const user = userEvent.setup();
    const { onImport } = renderForm();

    await user.type(screen.getByPlaceholderText('owner/name'), 'someone/probe');
    await user.type(screen.getByPlaceholderText('auto'), '7');
    await user.click(screen.getByRole('button', { name: 'Import head' }));

    expect(onImport).toHaveBeenCalledWith(expect.objectContaining({ num_classes: 7 }));
  });

  it('keeps the repo id after a failed import so it can be corrected', async () => {
    const user = userEvent.setup();
    const onImport = vi.fn().mockResolvedValue(false);
    render(
      <HeadImportForm
        headTypes={[headType()]}
        backbones={[backbone()]}
        busy={false}
        onImport={onImport}
      />,
    );

    const field = screen.getByPlaceholderText('owner/name');
    await user.type(field, 'someone/typo');
    await user.click(screen.getByRole('button', { name: 'Import head' }));

    expect(field).toHaveValue('someone/typo');
  });

  it('clears the repo id after a successful import', async () => {
    const user = userEvent.setup();
    renderForm();

    const field = screen.getByPlaceholderText('owner/name');
    await user.type(field, 'someone/probe');
    await user.click(screen.getByRole('button', { name: 'Import head' }));

    expect(field).toHaveValue('');
  });

  it('honours a user override of the preselected backbone', async () => {
    const user = userEvent.setup();
    const { onImport } = renderForm({
      backbones: [backbone('dinov2-small'), backbone('dinov2-base')],
    });

    await user.type(screen.getByPlaceholderText('owner/name'), 'someone/probe');
    await user.selectOptions(screen.getByDisplayValue('dinov2-small'), 'dinov2-base');
    await user.click(screen.getByRole('button', { name: 'Import head' }));

    expect(onImport).toHaveBeenCalledWith(
      expect.objectContaining({ backbone_id: 'dinov2-base' }),
    );
  });
});

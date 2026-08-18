/**
 * Tests for what the head card refuses and, more importantly, what it *says*.
 *
 * The wave rule is that an unusable head explains itself rather than being greyed out
 * or hidden. A disabled button with no reason is the failure these tests guard.
 */

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { CatalogEntry } from '../api/headCatalog';
import { HeadCatalogCard } from './HeadCatalogCard';

function entry(overrides: Partial<CatalogEntry> = {}): CatalogEntry {
  return {
    id: 'dinov2-linear-segmenter-ade20k.dinov2-small',
    title: 'DINOv2 linear segmenter (ADE20k)',
    task: 'segmentation',
    head_type_id: 'dinov2-linear-segmenter-ade20k',
    backbone_id: 'dinov2-small',
    trained_on: 'ADE20k, 150 classes',
    licence: 'Apache-2.0',
    size_bytes: 719_673,
    num_classes: 150,
    installed: false,
    installed_instance_id: null,
    backbone_installed: true,
    compatible: true,
    incompatible_reason: null,
    ...overrides,
  };
}

function renderCard(overrides: Partial<CatalogEntry> = {}, busy = false) {
  const onInstall = vi.fn();
  render(<HeadCatalogCard entry={entry(overrides)} busy={busy} onInstall={onInstall} />);
  return { onInstall };
}

describe('HeadCatalogCard', () => {
  it('shows provenance rather than a filename', () => {
    renderCard();
    expect(screen.getByText(/ADE20k, 150 classes/)).toBeInTheDocument();
    expect(screen.queryByText(/\.pth/)).not.toBeInTheDocument();
  });

  it('shows the licence and a human-readable size', () => {
    renderCard();
    expect(screen.getByText(/Apache-2\.0/)).toBeInTheDocument();
    expect(screen.getByText(/0\.7 MB/)).toBeInTheDocument();
  });

  it('offers Install when the backbone is present and compatible', () => {
    renderCard();
    expect(screen.getByRole('button', { name: 'Install' })).toBeEnabled();
  });

  it('blocks install and names the backbone to download first', () => {
    renderCard({ backbone_installed: false });
    expect(screen.getByRole('button', { name: 'Install' })).toBeDisabled();
    expect(screen.getByText(/Download the dinov2-small backbone first/)).toBeInTheDocument();
  });

  it('surfaces the backend reason when incompatible', () => {
    renderCard({
      compatible: false,
      incompatible_reason: 'Supports dinov2 backbones, but dinov3-vitb16 is dinov3.',
    });
    expect(screen.getByRole('button', { name: 'Install' })).toBeDisabled();
    expect(screen.getByText(/but dinov3-vitb16 is dinov3/)).toBeInTheDocument();
  });

  it('never disables without an explanation', () => {
    renderCard({ compatible: false, incompatible_reason: null });
    expect(screen.getByRole('button', { name: 'Install' })).toBeDisabled();
    expect(screen.getByText(/Not compatible/)).toBeInTheDocument();
  });

  it('replaces the button once installed', () => {
    renderCard({ installed: true, installed_instance_id: 'abc' });
    expect(screen.queryByRole('button', { name: 'Install' })).not.toBeInTheDocument();
    expect(screen.getByText(/Ready to use/)).toBeInTheDocument();
    expect(screen.getByText('Installed')).toBeInTheDocument();
  });

  it('shows progress while installing', () => {
    renderCard({}, true);
    expect(screen.getByRole('button', { name: 'Installing…' })).toBeDisabled();
  });

  it('omits the class count for depth, which has none', () => {
    renderCard({ num_classes: null, task: 'depth', trained_on: 'NYU Depth v2' });
    expect(screen.queryByText(/classes/)).not.toBeInTheDocument();
  });
});

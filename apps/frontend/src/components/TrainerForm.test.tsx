/**
 * Tests for what the trainer form refuses and why.
 *
 * The reason string matters as much as the disabled state: a dead button with no
 * explanation leaves the user guessing which of five fields is wrong.
 */

import { describe, expect, it } from 'vitest';

import type { BackboneInfo } from '../api/backbones';
import type { HeadTypeInfo } from '../api/heads';
import { blockingReason, type TrainerSelection } from './TrainerForm';

function backbone(overrides: Partial<BackboneInfo> = {}): BackboneInfo {
  return {
    id: 'dinov2-small',
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
    ...overrides,
  };
}

function headType(overrides: Partial<HeadTypeInfo> = {}): HeadTypeInfo {
  return {
    id: 'linear-classifier',
    task: 'classification',
    title: 'Linear classifier',
    description: 'A probe.',
    trainable: true,
    target_format: 'image-labels',
    consumes: 'cls',
    geometry: 'center-crop',
    metrics: ['accuracy', 'macro_f1'],
    primary_metric: 'accuracy',
    primary_metric_mode: 'max',
    render_hint: 'labels',
    compatible: true,
    incompatible_reason: null,
    ...overrides,
  };
}

const VALID: TrainerSelection = {
  datasetIds: ['ds1'],
  backboneId: 'dinov2-small',
  headTypeId: 'linear-classifier',
  epochs: 20,
  learningRate: 0.001,
  earlyStoppingPatience: 5,
};

describe('blockingReason', () => {
  it('allows a complete, compatible selection', () => {
    expect(blockingReason(VALID, [headType()], [backbone()])).toBeNull();
  });

  it('points at Admin when no backbone is installed', () => {
    const reason = blockingReason(VALID, [headType()], []);
    expect(reason).toContain('Admin');
  });

  it('requires at least one dataset', () => {
    const reason = blockingReason({ ...VALID, datasetIds: [] }, [headType()], [backbone()]);
    expect(reason).toContain('dataset');
  });

  it('requires a backbone', () => {
    const reason = blockingReason({ ...VALID, backboneId: '' }, [headType()], [backbone()]);
    expect(reason).toContain('backbone');
  });

  it('requires a head type', () => {
    const reason = blockingReason({ ...VALID, headTypeId: '' }, [headType()], [backbone()]);
    expect(reason).toContain('head type');
  });

  it('explains that a non-trainable head is still usable for inference', () => {
    const depth = headType({ id: 'linear-depth', title: 'Linear depth', trainable: false });
    const reason = blockingReason({ ...VALID, headTypeId: 'linear-depth' }, [depth], [backbone()]);
    expect(reason).toContain('pretrained default');
  });

  it('surfaces the backend incompatibility reason verbatim', () => {
    const incompatible = headType({
      compatible: false,
      incompatible_reason: 'Linear classifier supports dinov3 backbones, but dinov2-small is dinov2.',
    });
    expect(blockingReason(VALID, [incompatible], [backbone()])).toBe(
      'Linear classifier supports dinov3 backbones, but dinov2-small is dinov2.',
    );
  });
});

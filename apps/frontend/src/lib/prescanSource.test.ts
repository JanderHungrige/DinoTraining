/**
 * Mapping a session's configuration to a scan request (doc 53).
 *
 * The whole point of prescan is that it runs **the same model the session proposes with**,
 * so this mapping is the thing that must not drift. A wrong branch here filters on one
 * model's opinion and annotates with another's, and every disagreement then looks like a
 * bug in the proposer.
 */

import { describe, expect, it } from 'vitest';

import type { GeneratorConfig } from '../hooks/useGeneratorSession';
import type { ProposalSource } from '../hooks/useAnnotationSession';
import {
  generatorPrescanOptions,
  generatorPrescanSuggestions,
  prescanOptions,
  prescanSuggestions,
} from './prescanSource';

const PATHS = ['/a.png', '/b.png'];

describe('the Studio', () => {
  it('scans a head as a head', () => {
    const source: ProposalSource = {
      kind: 'head',
      backboneId: 'dinov2-small',
      instanceId: 'h1',
      scoreThreshold: 0.3,
    };
    expect(prescanOptions(source, PATHS, ['person'], 0.4)).toMatchObject({
      kind: 'head',
      backboneId: 'dinov2-small',
      instanceId: 'h1',
      labels: ['person'],
      scoreThreshold: 0.4,
    });
  });

  it('scans a detector as a foundation model', () => {
    const source: ProposalSource = {
      kind: 'foundation',
      foundationId: 'rf-detr-nano',
      scoreThreshold: 0.3,
    };
    expect(prescanOptions(source, PATHS, [], 0.3)).toMatchObject({
      kind: 'foundation',
      foundationId: 'rf-detr-nano',
    });
  });

  it('carries a concept when the detector needs one', () => {
    const source: ProposalSource = {
      kind: 'foundation',
      foundationId: 'grounded-sam',
      scoreThreshold: 0.3,
      concept: 'a cat',
    };
    expect(prescanOptions(source, PATHS, [], 0.3)).toMatchObject({ concept: 'a cat' });
  });

  it('omits the concept for a detector that ignores one', () => {
    // RF-DETR predicts its 91 COCO classes whatever is typed at it; sending a concept
    // would suggest otherwise to anyone reading the request.
    const source: ProposalSource = {
      kind: 'foundation',
      foundationId: 'rf-detr-nano',
      scoreThreshold: 0.3,
    };
    expect(prescanOptions(source, PATHS, [], 0.3)).not.toHaveProperty('concept');
  });

  it('scans a prompt with the same grounding model the Studio proposes with', () => {
    const source: ProposalSource = {
      kind: 'prompt',
      prompt: 'a cat. a dog.',
      boxThreshold: 0.3,
      textThreshold: 0.25,
    };
    expect(prescanOptions(source, PATHS, [], 0.3)).toMatchObject({
      kind: 'prompt',
      modelId: 'grounding-dino-tiny',
      prompt: 'a cat. a dog.',
      textThreshold: 0.25,
    });
  });

  it('suggests the phrases a prompt already names', () => {
    const source: ProposalSource = {
      kind: 'prompt',
      prompt: 'a cat. a dog.',
      boxThreshold: 0.3,
      textThreshold: 0.25,
    };
    expect(prescanSuggestions(source)).toEqual(['a cat', 'a dog']);
  });

  it('suggests nothing rather than something wrong for a head', () => {
    const source: ProposalSource = {
      kind: 'head',
      backboneId: 'dinov2-small',
      instanceId: 'h1',
      scoreThreshold: 0.3,
    };
    expect(prescanSuggestions(source)).toEqual([]);
  });
});

describe('the Dataset Generator', () => {
  const base = { datasetId: 'd1', images: { kind: 'folder', folder: '/x' } } as const;

  it('scans an expert run as a head', () => {
    const config: GeneratorConfig = {
      ...base,
      kind: 'expert',
      backboneId: 'dinov2-small',
      instanceId: 'h1',
      scoreThreshold: 0.3,
    };
    expect(generatorPrescanOptions(config, PATHS, ['bolt'], 0.5)).toMatchObject({
      kind: 'head',
      instanceId: 'h1',
      labels: ['bolt'],
    });
  });

  it('scans a foundation run as a foundation model', () => {
    const config: GeneratorConfig = {
      ...base,
      kind: 'foundation',
      foundationId: 'rf-detr-nano',
      scoreThreshold: 0.3,
    };
    expect(generatorPrescanOptions(config, PATHS, [], 0.3)).toMatchObject({
      kind: 'foundation',
      foundationId: 'rf-detr-nano',
    });
  });

  it('scans a mask run through the annotator registered as a foundation model', () => {
    // Only possible because doc 45 registered the mask annotators under the same ids.
    // Without it, mask mode would have needed a fourth scan kind of its own.
    const config: GeneratorConfig = {
      ...base,
      kind: 'masks',
      annotatorId: 'grounded-sam',
      concept: 'a bolt. a nut.',
      scoreThreshold: 0.3,
    };
    expect(generatorPrescanOptions(config, PATHS, [], 0.3)).toMatchObject({
      kind: 'foundation',
      foundationId: 'grounded-sam',
      concept: 'a bolt. a nut.',
    });
  });

  it('suggests the concept a mask run already names', () => {
    const config: GeneratorConfig = {
      ...base,
      kind: 'masks',
      annotatorId: 'grounded-sam',
      concept: 'a bolt. a nut.',
      scoreThreshold: 0.3,
    };
    expect(generatorPrescanSuggestions(config)).toEqual(['a bolt', 'a nut']);
  });

  it('passes the images it was given, not a copy of the folder', () => {
    const config: GeneratorConfig = {
      ...base,
      kind: 'foundation',
      foundationId: 'rf-detr-nano',
      scoreThreshold: 0.3,
    };
    expect(generatorPrescanOptions(config, PATHS, [], 0.3).imagePaths).toEqual(PATHS);
  });
});

/**
 * Turning the session's proposal source into a prescan request (doc 53).
 *
 * One function, in one place, because the whole point of prescan is that it runs **the same
 * model the session proposes with**. A second mapping — even a correct one today — is how
 * the two drift, and a drifted scan filters on one opinion while the canvas shows another.
 */

import type { StartPrescanOptions } from '../api/prescan';
import type { ProposalSource } from '../hooks/useAnnotationSession';
import type { GeneratorConfig } from '../hooks/useGeneratorSession';

export function prescanOptions(
  source: ProposalSource,
  imagePaths: readonly string[],
  labels: readonly string[],
  scoreThreshold: number,
): StartPrescanOptions {
  const common = { imagePaths, labels, scoreThreshold } as const;

  if (source.kind === 'head') {
    return {
      ...common,
      kind: 'head',
      backboneId: source.backboneId,
      instanceId: source.instanceId,
    };
  }
  if (source.kind === 'foundation') {
    return {
      ...common,
      kind: 'foundation',
      foundationId: source.foundationId,
      ...(source.concept ? { concept: source.concept } : {}),
    };
  }
  return {
    ...common,
    kind: 'prompt',
    // The catalogue id the Studio's own proposals use. Hard-coded in one place rather
    // than threaded through the session, which does not carry it either.
    modelId: 'grounding-dino-tiny',
    prompt: source.prompt,
    textThreshold: source.textThreshold,
  };
}

/** What to suggest in the "looking for" box.
 *
 *  A prompt source already names what the user wants, so it is the obvious default. A head
 *  or detector knows its classes but the session does not carry them, so nothing is
 *  suggested rather than something wrong. */
export function prescanSuggestions(source: ProposalSource): string[] {
  return source.kind === 'prompt'
    ? source.prompt
        .split(/[.,]/)
        .map((part) => part.trim())
        .filter(Boolean)
    : [];
}


/** The Dataset Generator's config, as a scan request (doc 53).
 *
 * Its three modes map onto the same three the Studio uses, with one substitution that is
 * only possible because of doc 45: a **mask** run names an annotator id, and those are now
 * registered as foundation models under the same id — so `grounded-sam` scans as a
 * concept-prompted detector and its box half does the filtering, exactly as it does in the
 * Studio. Without that, mask mode would have needed a fourth scan kind of its own.
 */
export function generatorPrescanOptions(
  config: GeneratorConfig,
  imagePaths: readonly string[],
  labels: readonly string[],
  scoreThreshold: number,
): StartPrescanOptions {
  const common = { imagePaths, labels, scoreThreshold } as const;

  if (config.kind === 'expert') {
    return {
      ...common,
      kind: 'head',
      backboneId: config.backboneId,
      instanceId: config.instanceId,
    };
  }
  if (config.kind === 'foundation') {
    return { ...common, kind: 'foundation', foundationId: config.foundationId };
  }
  return {
    ...common,
    kind: 'foundation',
    foundationId: config.annotatorId,
    concept: config.concept,
  };
}

/** What to suggest in the Generator's "looking for" box. A mask run already names its
 *  concept; the other two know their classes but the config does not carry them. */
export function generatorPrescanSuggestions(config: GeneratorConfig): string[] {
  return config.kind === 'masks'
    ? config.concept
        .split(/[.,]/)
        .map((part) => part.trim())
        .filter(Boolean)
    : [];
}

/**
 * The seven top-level areas of the app.
 *
 * `intro` leads deliberately (doc 38): it is the only tab that assumes you know nothing,
 * and a first-time user reads left to right. It is *not* the default tab — see
 * `DEFAULT_TAB` — because someone returning to work should land where the work is.
 */

export const TAB_IDS = [
  'intro',
  'studio',
  'trainer',
  'inference',
  'generator',
  'library',
  'admin',
  'api',
] as const;

export type TabId = (typeof TAB_IDS)[number];

export interface TabDefinition {
  readonly id: TabId;
  readonly label: string;
  /** One-line description of what the tab is for, shown while it is still a stub. */
  readonly hint: string;
  /** The wave that makes this tab functional — surfaced in the stub panels. */
  readonly wave: number;
}

export const TABS: readonly TabDefinition[] = Object.freeze([
  {
    id: 'intro',
    label: 'Start here',
    hint: 'What this app does, what a backbone and a head are, and what it cannot do yet.',
    wave: 7,
  },
  {
    id: 'studio',
    label: 'Annotation Studio',
    // Updated in Wave 5: a prompt is no longer the only way to get proposals.
    hint: 'Label a folder of images — from a text prompt, or from a head you trained.',
    wave: 1,
  },
  {
    id: 'trainer',
    // "Head Trainer" named only half of what the tab does. Fine-tuning a whole model
    // lived at the bottom of it under an <h3> and was, predictably, never found.
    label: 'Training',
    hint: 'Train a head on a frozen DINO backbone, or fine-tune a whole detector.',
    wave: 2,
  },
  {
    id: 'inference',
    label: 'Inference Viewer',
    // Webcam is backlogged, not built — an intro that points at it would be a lie.
    hint: 'Run trained heads and foundation models on one image, side by side.',
    wave: 3,
  },
  {
    id: 'generator',
    label: 'Dataset Generator',
    hint: 'Auto-annotate new images with a trained head or a concept prompt, then review.',
    wave: 4,
  },
  {
    id: 'library',
    label: 'Library',
    hint: 'Everything you have made — datasets, trained heads and fine-tuned models.',
    wave: 7,
  },
  {
    id: 'admin',
    label: 'Admin / Models',
    hint: 'Download and remove models, manage the HF token, cache dir, and device.',
    wave: 1,
  },
  {
    id: 'api',
    // Last, and a destination rather than a setting: you come here to copy something out.
    // Burying it in Admin would repeat the mistake that hid fine-tuning for three waves.
    label: 'API',
    hint: 'Hand this to your own AI assistant and let it drive the app.',
    wave: 9,
  },
] as const);

export const DEFAULT_TAB: TabId = 'studio';

export function isTabId(value: unknown): value is TabId {
  return typeof value === 'string' && (TAB_IDS as readonly string[]).includes(value);
}

export function getTab(id: TabId): TabDefinition {
  const tab = TABS.find((candidate) => candidate.id === id);
  if (!tab) {
    // Unreachable while TabId and TABS agree; throwing keeps that guarantee honest.
    throw new Error(`No tab definition for id: ${id}`);
  }
  return tab;
}

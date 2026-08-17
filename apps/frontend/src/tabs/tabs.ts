/** The five top-level areas of the app. Wave 1 fills in Studio and Admin. */

export const TAB_IDS = ['studio', 'trainer', 'inference', 'generator', 'admin'] as const;

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
    id: 'studio',
    label: 'Annotation Studio',
    hint: 'Point at an image folder, prompt Grounding DINO, label the boxes it proposes.',
    wave: 1,
  },
  {
    id: 'trainer',
    label: 'Head Trainer',
    hint: 'Train a head on a frozen DINO backbone and watch live metrics.',
    wave: 2,
  },
  {
    id: 'inference',
    label: 'Inference Viewer',
    hint: 'Run a backbone plus trained heads on an image or webcam, side by side.',
    wave: 3,
  },
  {
    id: 'generator',
    label: 'Dataset Generator',
    hint: 'Auto-annotate new data with trained expert heads, then review and save.',
    wave: 4,
  },
  {
    id: 'admin',
    label: 'Admin / Models',
    hint: 'Download and remove models, manage the HF token, cache dir, and device.',
    wave: 1,
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

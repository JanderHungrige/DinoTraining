/**
 * The top-level areas of the app.
 *
 * `intro` leads deliberately (doc 38): it is the only tab that assumes you know nothing,
 * and a first-time user reads left to right. It is *not* the default tab — see
 * `DEFAULT_TAB` — because someone returning to work should land where the work is.
 */

import type { Key } from '../i18n/catalogue';
import { ENGLISH, type Translator } from '../i18n/translate';

export const TAB_IDS = [
  'intro',
  'models',
  'inspect',
  'studio',
  'prepare',
  'trainer',
  'inference',
  'generator',
  'api',
  'settings',
] as const;

export type TabId = (typeof TAB_IDS)[number];

interface TabEntry {
  readonly id: TabId;
  /** Catalogue key of the tab's name (doc 112); translated where it is rendered. */
  readonly labelKey: Key;
  /** One-line description of what the tab is for, shown while it is still a stub. */
  readonly hintKey: Key;
  /** The wave that makes this tab functional — surfaced in the stub panels. */
  readonly wave: number;
}

export interface TabDefinition extends TabEntry {
  /** English name, for code outside the React tree. Rendered text uses `tabLabel`. */
  readonly label: string;
  /** English hint, for code outside the React tree. Rendered text uses `tabHint`. */
  readonly hint: string;
}

const ENTRIES: readonly TabEntry[] = [
  {
    id: 'intro',
    labelKey: 'app.tabs.introLabel',
    hintKey: 'app.tabs.introHint',
    wave: 7,
  },
  {
    // The entry point (doc 135): get models and data first. Replaces Admin and Library.
    id: 'models',
    labelKey: 'app.tabs.modelsLabel',
    hintKey: 'app.tabs.modelsHint',
    wave: 1,
  },
  {
    // Right after Start here (Jan, 2026-10-01): look at what you have before annotating
    // more, and come back after every round of the loop.
    id: 'inspect',
    labelKey: 'app.tabs.inspectLabel',
    hintKey: 'app.tabs.inspectHint',
    wave: 9,
  },
  {
    id: 'studio',
    // Updated in Wave 5: a prompt is no longer the only way to get proposals.
    labelKey: 'app.tabs.studioLabel',
    hintKey: 'app.tabs.studioHint',
    wave: 1,
  },
  {
    // Between annotating and training, because that is where it happens (doc 89).
    id: 'prepare',
    labelKey: 'app.tabs.prepareLabel',
    hintKey: 'app.tabs.prepareHint',
    wave: 11,
  },
  {
    id: 'trainer',
    // "Head Trainer" named only half of what the tab does. Fine-tuning a whole model
    // lived at the bottom of it under an <h3> and was, predictably, never found.
    labelKey: 'app.tabs.trainerLabel',
    hintKey: 'app.tabs.trainerHint',
    wave: 2,
  },
  {
    id: 'inference',
    // Webcam is backlogged, not built — an intro that points at it would be a lie.
    labelKey: 'app.tabs.inferenceLabel',
    hintKey: 'app.tabs.inferenceHint',
    wave: 3,
  },
  {
    id: 'generator',
    labelKey: 'app.tabs.generatorLabel',
    hintKey: 'app.tabs.generatorHint',
    wave: 4,
  },
  {
    id: 'api',
    // Last, and a destination rather than a setting: you come here to connect something.
    // Burying it in Admin would repeat the mistake that hid fine-tuning for three waves.
    labelKey: 'app.tabs.apiLabel',
    hintKey: 'app.tabs.apiHint',
    wave: 9,
  },
  {
    // Doc 164: after the loop, as settings are everywhere (Jan, 2026-10-02).
    id: 'settings',
    labelKey: 'app.tabs.settingsLabel',
    hintKey: 'app.tabs.settingsHint',
    wave: 16,
  },
];

export const TABS: readonly TabDefinition[] = Object.freeze(
  ENTRIES.map((entry) => ({
    ...entry,
    label: ENGLISH.t(entry.labelKey),
    hint: ENGLISH.t(entry.hintKey),
  })),
);

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

/** A tab's name in the current language. */
export function tabLabel(t: Translator['t'], id: TabId): string {
  return t(getTab(id).labelKey);
}

/** A tab's one-line hint in the current language. */
export function tabHint(t: Translator['t'], id: TabId): string {
  return t(getTab(id).hintKey);
}

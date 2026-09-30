/**
 * The Intro tab's prose, as data (doc 38).
 *
 * Separate from the component so the page stays under the line limit, and so a test can
 * assert on *what it claims* rather than on markup. That matters more here than elsewhere:
 * this is the one place in the app whose only job is to be true, and the fastest way for it
 * to become false is for someone to change a tab and never think about this file.
 *
 * The words themselves are catalogue keys (doc 112): each list is built by a function of a
 * `Translator`, and the English constants below are those functions applied to `ENGLISH`.
 *
 * Every `tab` reference below is a real `TabId`, checked by the compiler, so a renamed or
 * removed tab breaks the build rather than leaving the intro pointing at nothing.
 */

import { ENGLISH, type Key, type Translator } from '../i18n';
import type { TabId } from './tabs';

export interface IntroStage {
  readonly tab: TabId;
  readonly title: string;
  readonly what: string;
  /** Why this stage comes where it does. The order is the part nobody can guess. */
  readonly why: string;
}

export interface IntroConcept {
  readonly term: string;
  readonly body: string;
}

export function introLead({ t }: Translator): string {
  return t('intro.lead');
}

/** The loop, in the order the tabs run — which is the order they appear. */
const STAGE_TABS = [
  'studio',
  'prepare',
  'trainer',
  'inference',
  'generator',
  'inspect',
  'library',
  'admin',
  'api',
] as const satisfies readonly TabId[];

export function introStages({ t }: Translator): readonly IntroStage[] {
  return STAGE_TABS.map((tab) => ({
    tab,
    title: t(`intro.stage.${tab}.title`),
    what: t(`intro.stage.${tab}.what`),
    why: t(`intro.stage.${tab}.why`),
  }));
}

/** The three ideas the rest of the app assumes and never explains. */
const CONCEPTS = ['backbone', 'head', 'preprocessing'] as const;

export function introConcepts({ t }: Translator): readonly IntroConcept[] {
  return CONCEPTS.map((id) => ({
    term: t(`intro.concept.${id}.term`),
    body: t(`intro.concept.${id}.body`),
  }));
}

/**
 * What the app cannot do yet.
 *
 * Deliberately part of the intro. Someone who reads this and then goes looking for video
 * has been told; someone who is not told concludes the app is broken. Kept accurate as of
 * Wave 6 — anything fixed here should be *removed* from this list in the same commit.
 */
const LIMITS = ['stillImages', 'masks', 'detector', 'dragDrop', 'noise'] as const;

export function introLimits({ t }: Translator): readonly string[] {
  return LIMITS.map((id) => t(`intro.limit.${id}`));
}

/**
 * Which model to reach for, and what each is actually good at.
 *
 * Added after the question was asked out loud: "is a DINOv2 head not really suitable for
 * object detection?" It is a fair question with a nuanced answer, and the nuance was
 * previously only in `.mdd/docs/` where a user never looks.
 *
 * **Every number here was measured in this app**, on the datasets in it. They are cited
 * rather than described because "better for small objects" is an opinion and "0.556 against
 * 0.957 on the same rail data" is not. Anything restated here that later changes should be
 * re-measured, not adjusted to taste.
 */
export interface ModelGuideEntry {
  readonly name: string;
  /** The one-line answer: reach for this when… */
  readonly bestFor: string;
  readonly strengths: readonly string[];
  readonly weaknesses: readonly string[];
  /** Measured in this app, with the dataset named. Empty where nothing was measured. */
  readonly measured?: string;
}

/** One entry's keys. `measured` only where something was measured. */
interface GuideKeys {
  readonly name: Key;
  readonly bestFor: Key;
  readonly strengths: readonly Key[];
  readonly weaknesses: readonly Key[];
  readonly measured?: Key;
}

function guideKeys(id: string, weaknesses: number, measured: boolean): GuideKeys {
  // Built from a pattern, then checked against the catalogue by the test that renders it.
  const key = (what: string): Key => `intro.guide.${id}.${what}` as Key;
  return {
    name: key('name'),
    bestFor: key('bestFor'),
    strengths: [key('strength1'), key('strength2')],
    weaknesses: Array.from({ length: weaknesses }, (_, index) => key(`weakness${index + 1}`)),
    ...(measured ? { measured: key('measured') } : {}),
  };
}

const GUIDE: readonly GuideKeys[] = [
  guideKeys('classifier', 1, false),
  guideKeys('segmenter', 2, false),
  guideKeys('detector', 2, true),
  guideKeys('rfdetr', 2, true),
  guideKeys('sam', 2, false),
];

export function modelGuide({ t }: Translator): readonly ModelGuideEntry[] {
  return GUIDE.map((entry) => ({
    name: t(entry.name),
    bestFor: t(entry.bestFor),
    strengths: entry.strengths.map((point) => t(point)),
    weaknesses: entry.weaknesses.map((point) => t(point)),
    ...(entry.measured ? { measured: t(entry.measured) } : {}),
  }));
}

/** The one-paragraph answer, for someone who will not read the table. */
export function modelGuideLead({ t }: Translator): string {
  return t('intro.guide.lead');
}

/** English, for tests and for callers outside the React tree. */
export const INTRO_LEAD = introLead(ENGLISH);
export const INTRO_STAGES: readonly IntroStage[] = Object.freeze(introStages(ENGLISH));
export const INTRO_CONCEPTS: readonly IntroConcept[] = Object.freeze(introConcepts(ENGLISH));
export const INTRO_LIMITS: readonly string[] = Object.freeze(introLimits(ENGLISH));
export const MODEL_GUIDE: readonly ModelGuideEntry[] = Object.freeze(modelGuide(ENGLISH));
export const MODEL_GUIDE_LEAD = modelGuideLead(ENGLISH);

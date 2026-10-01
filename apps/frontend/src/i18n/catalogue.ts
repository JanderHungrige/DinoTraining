/**
 * Every namespace, merged (doc 111). A namespace is added here once — `en/<ns>.ts` and
 * `de/<ns>.ts` — and the German one is type-checked against the English one.
 */

import { commonDe } from './de/common';
import { commonEn } from './en/common';
import { appDe } from './de/app';
import { appEn } from './en/app';
import { introDe } from './de/intro';
import { introEn } from './en/intro';
import { studioDe } from './de/studio';
import { studioEn } from './en/studio';
import { phrasesDe } from './de/phrases';
import { phrasesEn } from './en/phrases';
import { prepareDe } from './de/prepare';
import { prepareEn } from './en/prepare';
import { trainingDe } from './de/training';
import { trainingEn } from './en/training';
import { runDe } from './de/run';
import { runEn } from './en/run';
import { generatorDe } from './de/generator';
import { generatorEn } from './en/generator';
import { adminDe } from './de/admin';
import { adminEn } from './en/admin';
import { setupDe } from './de/setup';
import { setupEn } from './en/setup';
import { guideDe } from './de/guide';
import { guideEn } from './en/guide';
import { datasetsDe } from './de/datasets';
import { datasetsEn } from './en/datasets';

export const en = {
  ...commonEn,
  ...appEn,
  ...introEn,
  ...studioEn,
  ...phrasesEn,
  ...prepareEn,
  ...trainingEn,
  ...runEn,
  ...generatorEn,
  ...adminEn,
  ...setupEn,
  ...guideEn,
  ...datasetsEn,
} as const;

export type Key = keyof typeof en;

export const de: { readonly [K in Key]: string } = {
  ...commonDe,
  ...appDe,
  ...introDe,
  ...studioDe,
  ...phrasesDe,
  ...prepareDe,
  ...trainingDe,
  ...runDe,
  ...generatorDe,
  ...adminDe,
  ...setupDe,
  ...guideDe,
  ...datasetsDe,
};

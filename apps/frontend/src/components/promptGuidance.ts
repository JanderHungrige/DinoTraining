/**
 * What to say about a prompt, per mode (doc 39).
 *
 * By Wave 7 "the prompt" is three different things, and which one you are looking at is not
 * visible from the field itself:
 *
 *   - **Grounding DINO text** — several phrases, full-stop separated, in the Studio.
 *   - **A trained head** — no prompt at all, because the head knows its own classes.
 *   - **A concept** — one phrase for SAM 3, several for Grounded SAM, in the Generator.
 *
 * Kept as data next to the components that use it so the wording is reviewable in one
 * place. Not shared *text* — the three cases genuinely say different things — but a shared
 * home, so the next person adding a fourth prompting mode finds the other three first.
 */

import { ENGLISH, type Translator } from '../i18n';

/** Grounding DINO's syntax, which is not guessable from an empty field. In English; a
 *  component renders `studio.guidance.groundingDino` through its own translator. */
export const GROUNDING_DINO_HINT = ENGLISH.t('studio.guidance.groundingDino');

/**
 * Why head mode has no prompt. Naming the head's own classes answers the question the
 * missing field raises — "so what *will* it look for?" — instead of only explaining the
 * absence.
 */
export function headModeHint(classNames: readonly string[], { t }: Translator = ENGLISH): string {
  if (classNames.length === 0) return t('studio.guidance.headNone');
  const listed =
    classNames.length <= 4
      ? classNames.join(', ')
      : t('studio.guidance.andMore', { list: classNames.slice(0, 4).join(', '), count: classNames.length - 4 });
  return t('studio.guidance.head', { classes: listed });
}

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

/** Grounding DINO's syntax, which is not guessable from an empty field. */
export const GROUNDING_DINO_HINT =
  'Grounding DINO reads each phrase between full stops as a separate thing to look for. ' +
  'One label type: “a bolt”. Several: “a bolt. a nut. a washer.” Lower case, a leading ' +
  '“a”, and a full stop after each — that is the form it was trained on. It will also ' +
  'find things you did not ask for, which is what the reject key is for.';

/**
 * Why head mode has no prompt. Naming the head's own classes answers the question the
 * missing field raises — "so what *will* it look for?" — instead of only explaining the
 * absence.
 */
export function headModeHint(classNames: readonly string[]): string {
  if (classNames.length === 0) {
    return 'No prompt here: a trained head already knows what it is looking for. It proposes its own classes, and you accept, reject or correct them.';
  }
  const listed =
    classNames.length <= 4
      ? classNames.join(', ')
      : `${classNames.slice(0, 4).join(', ')} and ${classNames.length - 4} more`;
  return `No prompt here: this head was trained to find ${listed}. It proposes those and nothing else — prompting is for models that take words, and this one takes an image.`;
}

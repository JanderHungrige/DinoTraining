/**
 * Autoplay for the Dataset Generator (doc 71): propose → hold → save → next, from the image
 * the user is on to the end of the list, until stopped.
 *
 * A plain async function over paths, deliberately outside React. After every `await` the
 * component's state is stale, and a loop that read it would propose for one image and save
 * under another's path. Here the loop owns its own position and hands each result to the
 * UI through `show`, so what is saved is always what was proposed for that path.
 *
 * Stopping is honoured at every step, and it never saves the image it stopped on. A stop
 * during the hold means "that one looks wrong", which is the whole reason the hold exists.
 */

import type { ImageReview } from './generatorSave';

export interface AutoplayProgress {
  /** Images dealt with so far in this run, including skipped and failed ones. */
  readonly done: number;
  /** Images this run will visit: from the start image to the end of the list. */
  readonly total: number;
  readonly saved: number;
  readonly empty: number;
  readonly failed: number;
  readonly skipped: number;
}

export type AutoplayEnd = 'finished' | 'stopped' | 'save-failed';

export interface AutoplayReport extends AutoplayProgress {
  readonly end: AutoplayEnd;
  /** The image the run was on when it ended: where the user should be left. */
  readonly lastIndex: number;
  /** The most recent proposal failure, so a run of failures has a reason on screen. */
  readonly lastError: string | null;
}

export interface AutoplayRun {
  readonly paths: readonly string[];
  readonly start: number;
  /** Hidden mode: no drawing and no hold, just progress (doc 71). */
  readonly hidden: boolean;
  readonly holdMs: number;
  readonly signal: AbortSignal;
  readonly propose: (path: string) => Promise<ImageReview>;
  readonly save: (review: ImageReview) => Promise<boolean>;
  readonly isSaved: (path: string) => boolean;
  /** Visible mode only: move to an image (null review), then show what was proposed. */
  readonly show: (index: number, review: ImageReview | null) => void;
  readonly onProgress: (progress: AutoplayProgress) => void;
}

/** Resolves after `ms`, or at once when the signal aborts. Never rejects. */
export function holdFor(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) {
      resolve();
      return;
    }
    const timer = setTimeout(resolve, ms);
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}

function found(review: ImageReview): boolean {
  return review.boxes.length > 0 || review.masks.length > 0;
}

interface Tally {
  done: number;
  total: number;
  saved: number;
  empty: number;
  failed: number;
  skipped: number;
}

/** What happened to one image: counted under `outcome`, or the run has to end. */
type Step = { readonly outcome: 'saved' | 'empty' | 'failed'; readonly error?: string } | AutoplayEnd;

async function step(run: AutoplayRun, index: number, path: string): Promise<Step> {
  if (!run.hidden) run.show(index, null);

  let review: ImageReview;
  try {
    review = await run.propose(path);
  } catch (caught) {
    // One bad image must not end an unattended run over hundreds.
    return {
      outcome: 'failed',
      error: caught instanceof Error ? caught.message : 'Nothing could be proposed.',
    };
  }

  if (!run.hidden) run.show(index, review);
  if (run.signal.aborted) return 'stopped';
  if (!found(review)) return { outcome: 'empty' };

  if (!run.hidden) {
    await holdFor(run.holdMs, run.signal);
    if (run.signal.aborted) return 'stopped';
  }
  // A failed save is not one bad image; the next save would fail the same way. Stop on the
  // image, with its review on screen, rather than skip past unsaved work.
  return (await run.save(review)) ? { outcome: 'saved' } : 'save-failed';
}

export async function runAutoplay(run: AutoplayRun): Promise<AutoplayReport> {
  const tally: Tally = {
    done: 0,
    total: Math.max(0, run.paths.length - run.start),
    saved: 0,
    empty: 0,
    failed: 0,
    skipped: 0,
  };
  let lastIndex = Math.min(run.start, Math.max(0, run.paths.length - 1));
  let lastError: string | null = null;
  const report = (end: AutoplayEnd): AutoplayReport => ({ ...tally, end, lastIndex, lastError });

  for (let index = run.start; index < run.paths.length; index += 1) {
    if (run.signal.aborted) return report('stopped');
    const path = run.paths[index]!;

    // Saved earlier in this session: the user's review stands, and re-proposing would
    // overwrite it. Counted, so the progress still reaches 100 %.
    if (run.isSaved(path)) {
      tally.skipped += 1;
    } else {
      lastIndex = index;
      const result = await step(run, index, path);
      if (typeof result === 'string') return report(result);
      tally[result.outcome] += 1;
      if (result.error !== undefined) lastError = result.error;
    }
    tally.done += 1;
    run.onProgress({ ...tally });
  }
  return report('finished');
}

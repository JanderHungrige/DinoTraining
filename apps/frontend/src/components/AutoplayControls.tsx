/**
 * Play / Stop and the "hidden" box, in the Generator's toolbar (doc 71).
 *
 * Stop is never disabled: it is the one control that must work while everything else is
 * locked, because stopping to correct a wrong box is what the half-second hold is for.
 */

import type { JSX } from 'react';

import type { Autoplay } from '../hooks/useAutoplay';

export interface AutoplayControlsProps {
  readonly autoplay: Autoplay;
  /** False while a manual proposal or save is in flight, or there is nothing to play. */
  readonly canPlay: boolean;
}

export function AutoplayControls({ autoplay, canPlay }: AutoplayControlsProps): JSX.Element {
  const { running, hidden, progress } = autoplay;

  return (
    <span className="genbar__pair genbar__autoplay">
      {running ? (
        <button type="button" className="btn genbar__stop" onClick={autoplay.stop}>
          ■ Stop
        </button>
      ) : (
        <button
          type="button"
          className="btn"
          disabled={!canPlay}
          onClick={autoplay.play}
          title="Propose, show for half a second, save, and move on — from this image to the last"
        >
          ▶ Play
        </button>
      )}
      <label className="genbar__auto" title="Run without drawing each image; show progress only">
        <input
          type="checkbox"
          checked={hidden}
          disabled={running}
          aria-label="Run hidden, without drawing each image"
          onChange={(event) => autoplay.setHidden(event.target.checked)}
        />
        hidden
      </label>
      {running && !hidden && progress && (
        <span className="genbar__count" role="status">
          {progress.done} / {progress.total}
        </span>
      )}
    </span>
  );
}

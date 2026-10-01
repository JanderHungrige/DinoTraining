/**
 * Start analysis / Stop in the Generator's toolbar, and the "Run hidden" box for the
 * options row below it (doc 71). The button said "Play", which read as playing back what
 * was already annotated rather than analysing the images (Jan, 2026-09-30).
 *
 * Stop is never disabled: it is the one control that must work while everything else is
 * locked, because stopping to correct a wrong box is what the half-second hold is for.
 */

import type { JSX } from 'react';

import type { Autoplay } from '../hooks/useAutoplay';
import { useT } from '../i18n';

export interface AutoplayControlsProps {
  readonly autoplay: Autoplay;
  /** False while a manual proposal or save is in flight, or there is nothing to play. */
  readonly canPlay: boolean;
}

export function AutoplayControls({ autoplay, canPlay }: AutoplayControlsProps): JSX.Element {
  const { t } = useT();
  const { running, hidden, progress } = autoplay;

  return (
    <span className="genbar__pair genbar__autoplay">
      {running ? (
        <button type="button" className="btn genbar__stop" onClick={autoplay.stop}>
          {t('generator.autoplay.stop')}
        </button>
      ) : (
        <button
          type="button"
          className="btn"
          disabled={!canPlay}
          onClick={autoplay.play}
          title={t('generator.autoplay.startTitle')}
        >
          {t('generator.autoplay.start')}
        </button>
      )}
      {running && !hidden && progress && (
        <span className="genbar__count" role="status">
          {progress.done} / {progress.total}
        </span>
      )}
    </span>
  );
}

/** The "Run hidden" choice, shown with the other automation boxes below the buttons. */
export function AutoplayHiddenOption({ autoplay }: { readonly autoplay: Autoplay }): JSX.Element {
  const { t } = useT();
  return (
    <label className="genbar__auto" title={t('generator.autoplay.hiddenTitle')}>
      <input
        type="checkbox"
        checked={autoplay.hidden}
        disabled={autoplay.running}
        aria-label={t('generator.autoplay.hiddenAria')}
        onChange={(event) => autoplay.setHidden(event.target.checked)}
      />
      {t('generator.autoplay.hidden')}
    </label>
  );
}

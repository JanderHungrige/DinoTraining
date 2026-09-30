/**
 * One coloured bar per class under the player, marking the frames it appears on (doc 75).
 *
 * Requested: *"colored annotation bars below the video, indicating where which annotation
 * can be found. Enable selecting an annotation bar by clicking and press a button to jump
 * to first annotation."*
 *
 * A bar is a real button (it selects its class, `aria-pressed`, and names how often the
 * class appears), and the jumps are ordinary buttons beside the bars, so all of it works
 * from the keyboard. The colour is the class's, from the same palette the boxes use.
 */

import type { JSX } from 'react';

import { useT } from '../i18n';
import { classColour, toCssColour } from '../lib/overlayPalette';
import {
  classesIn,
  countFrames,
  firstOccurrence,
  nextOccurrence,
  previousOccurrence,
  segmentsFor,
  type TimelineFrame,
} from '../lib/timeline';

export interface AnnotationTimelineProps {
  readonly frames: readonly TimelineFrame[];
  /** The dataset's classes, sorted: the index is the colour. */
  readonly classNames: readonly string[];
  readonly index: number;
  readonly selected: string | null;
  readonly onSelect: (name: string | null) => void;
  readonly onSeek: (position: number) => void;
}

function percent(position: number, length: number): string {
  return `${(position / Math.max(1, length)) * 100}%`;
}

export function AnnotationTimeline({
  frames,
  classNames,
  index,
  selected,
  onSelect,
  onSeek,
}: AnnotationTimelineProps): JSX.Element {
  const { t } = useT();
  const present = classesIn(frames, classNames);
  const active = selected !== null && present.includes(selected) ? selected : null;
  const jump = (target: number | null): void => {
    if (target !== null) onSeek(target);
  };

  if (present.length === 0) {
    return <p className="timeline__empty">{t('generator.timeline.empty')}</p>;
  }

  return (
    <div className="timeline">
      <div className="timeline__rows">
        {present.map((name) => {
          const colour = toCssColour(classColour(classNames.indexOf(name)));
          const count = countFrames(frames, name);
          return (
            <button
              key={name}
              type="button"
              className={`timeline__row${active === name ? ' timeline__row--selected' : ''}`}
              aria-pressed={active === name}
              aria-label={t('generator.timeline.barAria', { name, count, total: frames.length })}
              onClick={() => onSelect(active === name ? null : name)}
            >
              <span className="timeline__name">
                <span className="timeline__swatch" style={{ background: colour }} />
                {name}
              </span>
              <span className="timeline__track">
                {segmentsFor(frames, name).map((segment) => (
                  <span
                    key={segment.start}
                    className="timeline__segment"
                    style={{
                      left: percent(segment.start, frames.length),
                      width: percent(segment.end - segment.start + 1, frames.length),
                      background: colour,
                    }}
                  />
                ))}
                <span
                  className="timeline__playhead"
                  style={{ left: percent(index + 0.5, frames.length) }}
                  aria-hidden="true"
                />
              </span>
            </button>
          );
        })}
      </div>

      <div className="timeline__jumps" role="group" aria-label={t('generator.timeline.jumps')}>
        <span className="timeline__hint">
          {active ? `${active}:` : t('generator.timeline.hint')}
        </span>
        <button
          type="button"
          className="btn btn--small"
          disabled={active === null}
          onClick={() => active && jump(firstOccurrence(frames, active))}
        >
          {t('generator.timeline.first')}
        </button>
        <button
          type="button"
          className="btn btn--small"
          disabled={active === null || previousOccurrence(frames, active, index) === null}
          onClick={() => active && jump(previousOccurrence(frames, active, index))}
        >
          {t('generator.timeline.previous')}
        </button>
        <button
          type="button"
          className="btn btn--small"
          disabled={active === null || nextOccurrence(frames, active, index) === null}
          onClick={() => active && jump(nextOccurrence(frames, active, index))}
        >
          {t('generator.timeline.next')}
        </button>
      </div>
    </div>
  );
}

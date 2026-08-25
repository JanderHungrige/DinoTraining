/**
 * The box review list (doc 47) — the Studio's primary surface for detection output.
 *
 * Click-to-cycle on the canvas is a fine way to review *a few* boxes you drew yourself. It
 * is a poor way to review thirty a detector proposed: the verdict is hidden behind however
 * many clicks the cycle needs, a covered box cannot be reached at all, and there is nowhere
 * to see what class a box actually carries.
 *
 * So each box gets a row: its number, its class, its probability, and four buttons that set
 * a verdict in **one** click rather than cycling to it. The number is the same number drawn
 * on the box, which is what lets a person look at the image and find the row.
 */

import type { JSX } from 'react';

import { hasScores, type NumberedBox } from '../lib/boxReview';
import { ClassPicker } from './ClassPicker';
import type { CanvasBox, Label } from '../types/annotation';

export interface BoxReviewListProps {
  readonly boxes: readonly NumberedBox[];
  /** Every box not on screen, whatever the reason — this is what filters the list. */
  readonly hidden: ReadonlySet<string>;
  /** The subset the *score slider* is filtering. Separate from `hidden` because the two
   *  read differently and act differently: "below cutoff" is a claim about the score, and
   *  `Remove N below` must never discard a box the user merely got out of the way. */
  readonly belowCutoff?: ReadonlySet<string>;
  readonly selectedId: string | null;
  readonly threshold: number;
  readonly onSelect: (id: string | null) => void;
  readonly onLabel: (id: string, label: Label) => void;
  readonly onRename: (id: string, text: string) => void;
  readonly onRemove: (id: string) => void;
  readonly onThreshold: (threshold: number) => void;
  readonly onRemoveHidden: () => void;
  /** Every class a box can be given (doc 60). Empty until the vocabulary loads, which is
   *  why the picker still lists whatever class a box already carries. */
  readonly classes: readonly string[];
  /** Create a class. Resolves to the name as stored. */
  readonly onCreateClass: (name: string) => Promise<string | null>;
  /** Rename a class across every box on this image. Omitted where that has no meaning. */
  readonly onRenameClass?: (from: string, to: string) => void;
  readonly disabled?: boolean;
}

/** One click each, rather than cycling. `null` is remove. */
const VERDICTS: readonly (readonly [Label | null, string, string])[] = [
  ['positive', '✓', 'True'],
  ['negative', '✗', 'False'],
  ['unclear', '?', 'Not sure'],
  [null, '🗑', 'Remove'],
];

const EMPTY: ReadonlySet<string> = new Set<string>();

export function BoxReviewList({
  boxes,
  hidden,
  belowCutoff = EMPTY,
  selectedId,
  threshold,
  onSelect,
  onLabel,
  onRename,
  onRemove,
  onThreshold,
  onRemoveHidden,
  classes,
  onCreateClass,
  onRenameClass,
  disabled = false,
}: BoxReviewListProps): JSX.Element {
  const all = boxes.map((entry) => entry.box);
  const scored = hasScores(all);
  const visible = boxes.filter((entry) => !hidden.has(entry.box.id));
  const concealed = [...hidden].filter((id) => !belowCutoff.has(id)).length;

  return (
    <aside className="review" aria-label="Boxes">
      <header className="review__head">
        <h3 className="review__title">
          {visible.length} box{visible.length === 1 ? '' : 'es'}
          {/* Counted apart, because "below cutoff" is a claim about the score and would be
              a lie about a box the reviewer simply hid. */}
          {belowCutoff.size > 0 && (
            <span className="review__dim"> · {belowCutoff.size} below cutoff</span>
          )}
          {concealed > 0 && <span className="review__dim"> · {concealed} hidden</span>}
        </h3>
      </header>

      {scored && (
        <div className="review__threshold">
          <label htmlFor="review-threshold">
            Show above <span className="review__value">{threshold.toFixed(2)}</span>
          </label>
          <input
            id="review-threshold"
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={threshold}
            disabled={disabled}
            onChange={(event) => onThreshold(Number(event.target.value))}
          />
          {/* Hiding and removing are deliberately two actions. The slider is reversible
              and costs nothing to explore; discarding is neither, so it is a button that
              says how many. */}
          <button
            type="button"
            className="btn btn--small"
            disabled={disabled || belowCutoff.size === 0}
            onClick={onRemoveHidden}
          >
            Remove {belowCutoff.size} below
          </button>
        </div>
      )}

      {visible.length === 0 ? (
        <p className="review__empty" role="status">
          {all.length === 0
            ? 'No boxes yet. Run a model, or drag on the image to draw one.'
            : concealed > 0 && belowCutoff.size === 0
              ? 'Every box is hidden. Show them again to review them.'
              : 'Every box is below the cutoff. Lower it to see them.'}
        </p>
      ) : (
        <ul className="review__list">
          {visible.map(({ box, number }) => (
            <Row
              key={box.id}
              box={box}
              number={number}
              selected={box.id === selectedId}
              disabled={disabled}
              onSelect={onSelect}
              onLabel={onLabel}
              onRename={onRename}
              onRemove={onRemove}
              classes={classes}
              onCreateClass={onCreateClass}
              {...(onRenameClass ? { onRenameClass } : {})}
            />
          ))}
        </ul>
      )}
    </aside>
  );
}

interface RowProps {
  readonly box: CanvasBox;
  readonly number: number;
  readonly selected: boolean;
  readonly disabled: boolean;
  readonly onSelect: (id: string | null) => void;
  readonly onLabel: (id: string, label: Label) => void;
  readonly onRename: (id: string, text: string) => void;
  readonly onRemove: (id: string) => void;
  readonly classes: readonly string[];
  readonly onCreateClass: (name: string) => Promise<string | null>;
  readonly onRenameClass?: (from: string, to: string) => void;
}

function Row({
  box,
  number,
  selected,
  disabled,
  onSelect,
  onLabel,
  onRename,
  onRemove,
  classes,
  onCreateClass,
  onRenameClass,
}: RowProps): JSX.Element {
  const percent = box.score === undefined ? null : `${(box.score * 100).toFixed(0)}%`;

  return (
    <li
      className={`review__row review__row--${box.label}${selected ? ' review__row--selected' : ''}`}
      onMouseEnter={() => onSelect(box.id)}
    >
      <span className="review__number" aria-hidden="true">
        {number}
      </span>

      {/* A picker rather than a free-text field (doc 60). Typing worked for a box you had
          just drawn and knew the name of; it had no memory of the last thirty boxes, and no
          way for a class to exist before something was labelled with it. Retyping — the
          reason doc 47 chose an input — becomes the rename affordance, which corrects every
          box carrying the class rather than one. */}
      <ClassPicker
        value={box.text ?? ''}
        options={classes}
        label={`Class of box ${number}`}
        disabled={disabled}
        onChange={(name) => onRename(box.id, name)}
        onCreate={onCreateClass}
        {...(onRenameClass ? { onRename: onRenameClass } : {})}
      />

      <span className="review__score">{percent ?? '—'}</span>

      <span className="review__verdicts">
        {VERDICTS.map(([label, glyph, title]) => (
          <button
            key={title}
            type="button"
            className={`review__verdict${label !== null && box.label === label ? ' review__verdict--on' : ''}`}
            title={title}
            aria-label={`${title}, box ${number}`}
            aria-pressed={label === null ? undefined : box.label === label}
            disabled={disabled}
            onClick={() => (label === null ? onRemove(box.id) : onLabel(box.id, label))}
          >
            <span aria-hidden="true">{glyph}</span>
          </button>
        ))}
      </span>
    </li>
  );
}

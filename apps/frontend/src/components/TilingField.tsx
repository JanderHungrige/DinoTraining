/**
 * The grid to cut a frame into before running (doc 62).
 *
 * **Off by default, and it never turns itself on.** The same head should be runnable
 * either way — a tile-trained head over a close-up crop wants no grid — so this is a
 * per-run choice, not a property of the head. A control that silently enabled itself would
 * make two runs of "the same" configuration differ.
 *
 * **But undiscoverable is its own failure**, and the failure it guards against is silent:
 * a head trained on 616 px tiles finds nothing on a 2464 px frame, and the run succeeds
 * with an empty list. So when the app can tell — a head records the datasets it trained on,
 * and those datasets' images record their width — it says so, next to the control, and
 * leaves the decision alone.
 */

import type { JSX } from 'react';

import { isWholeFrame, type TileGrid } from '../api/inference';

export interface TilingFieldProps {
  readonly grid: TileGrid;
  readonly onChange: (grid: TileGrid) => void;
  /**
   * Median width of the images the selected heads trained on, when they agree on one.
   * Null when unknown, which is expected — a dataset can be deleted after training.
   */
  readonly trainedWidth: number | null;
  /** Natural width of the image on screen, once it has loaded. */
  readonly imageWidth: number | null;
  readonly disabled?: boolean;
}

/**
 * How much bigger the frame has to be before tiling is worth mentioning.
 *
 * 1.5 rather than 1.0 because a small difference is normal — a head trained at 448 px on
 * 500 px photos is fine on 600 px ones. The case this is for is an order of magnitude:
 * 616 px tiles against a 2464 px frame is 4x, where the object the head learned to find
 * arrives a quarter of the size and below the detector's stride.
 */
const SUGGEST_ABOVE = 1.5;

export function suggestsTiling(trainedWidth: number | null, imageWidth: number | null): boolean {
  if (!trainedWidth || !imageWidth) return false;
  return imageWidth / trainedWidth >= SUGGEST_ABOVE;
}

/**
 * A grid that would bring the frame back to roughly the width the head trained on.
 *
 * Offered as the starting point when the hint fires, so the common case is one click
 * rather than arithmetic. Square-ish rather than exact: the point is to get the object
 * above the stride, and a 4x3 over a 3:2 frame does that as well as a 4x2.7 would.
 */
export function suggestedGrid(trainedWidth: number, imageWidth: number): number {
  return Math.max(2, Math.min(8, Math.round(imageWidth / trainedWidth)));
}

export function TilingField({
  grid,
  onChange,
  trainedWidth,
  imageWidth,
  disabled = false,
}: TilingFieldProps): JSX.Element {
  const on = !isWholeFrame(grid);
  const suggest = suggestsTiling(trainedWidth, imageWidth);

  const toggle = (enabled: boolean): void => {
    if (!enabled) {
      onChange({ ...grid, columns: 1, rows: 1 });
      return;
    }
    const size = trainedWidth && imageWidth ? suggestedGrid(trainedWidth, imageWidth) : 3;
    onChange({ ...grid, columns: size, rows: Math.max(2, size - 1) });
  };

  return (
    <div className="tiling">
      <label className="tiling__toggle">
        <input
          type="checkbox"
          checked={on}
          disabled={disabled}
          onChange={(event) => toggle(event.target.checked)}
        />
        Tile the image
      </label>

      {on && (
        <span className="tiling__grid">
          <label className="tiling__num">
            <span>Columns</span>
            <input
              type="number"
              min={1}
              max={16}
              value={grid.columns}
              disabled={disabled}
              onChange={(event) =>
                onChange({ ...grid, columns: clamp(event.target.value, grid.columns) })
              }
            />
          </label>
          <span aria-hidden="true" className="tiling__times">
            ×
          </span>
          <label className="tiling__num">
            <span>Rows</span>
            <input
              type="number"
              min={1}
              max={16}
              value={grid.rows}
              disabled={disabled}
              onChange={(event) =>
                onChange({ ...grid, rows: clamp(event.target.value, grid.rows) })
              }
            />
          </label>
          <span className="tiling__count">
            {grid.columns * grid.rows} tile{grid.columns * grid.rows === 1 ? '' : 's'}
          </span>
        </span>
      )}

      {/* Shown whether or not tiling is on: it is as useful for explaining an empty
          result as for preventing one. */}
      {suggest && trainedWidth && imageWidth && (
        <p className="tiling__hint" role="note">
          This head trained on {trainedWidth} px images and this one is {imageWidth} px.
          Objects arrive about {(imageWidth / trainedWidth).toFixed(1)}× smaller than it
          learned to find{on ? '.' : ' — tiling is probably needed.'}
        </p>
      )}
    </div>
  );
}

/**
 * A number input can be empty mid-edit; keep the last good value.
 *
 * The empty check has to come first and be its own case. `Number('')` is **0**, which is
 * perfectly finite, so a `Number.isFinite` guard alone lets it through to be clamped to 1
 * — and 1 column is silently *no tiling*. Backspacing over the field to retype it would
 * have turned the feature off.
 */
function clamp(raw: string, fallback: number): number {
  if (raw.trim() === '') return fallback;
  const value = Number(raw);
  if (!Number.isFinite(value)) return fallback;
  return Math.max(1, Math.min(16, Math.round(value)));
}

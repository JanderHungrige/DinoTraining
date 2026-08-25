/**
 * The tiling control and its hint (doc 62).
 *
 * The hint is the interesting part. The failure it guards against is *silent* — a head
 * trained on 616 px tiles finds nothing on a 2464 px frame and the run succeeds with an
 * empty list — so the app has to volunteer what it knows. What it must never do is act on
 * it: two runs of "the same" configuration differing because a control turned itself on is
 * a worse bug than the one it would prevent.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { NO_TILING, type TileGrid } from '../api/inference';
import { TilingField, suggestedGrid, suggestsTiling } from './TilingField';

function renderField(over: Partial<Parameters<typeof TilingField>[0]> = {}) {
  const onChange = vi.fn<(grid: TileGrid) => void>();
  render(
    <TilingField
      grid={NO_TILING}
      onChange={onChange}
      trainedWidth={null}
      imageWidth={null}
      {...over}
    />,
  );
  return { onChange, user: userEvent.setup() };
}

describe('when it suggests tiling', () => {
  it('says nothing without both numbers', () => {
    // A dataset can be deleted after training, so a null training width is expected and
    // must not produce a confident claim.
    expect(suggestsTiling(null, 2464)).toBe(false);
    expect(suggestsTiling(616, null)).toBe(false);
  });

  it('says nothing when the sizes are close', () => {
    // A head trained at 448 on 500px photos is fine on 600px ones. Warning there would
    // train the user to ignore the hint.
    expect(suggestsTiling(500, 600)).toBe(false);
  });

  it('speaks up at the order of magnitude that actually breaks', () => {
    // 616px tiles against a 2464px frame: the object arrives a quarter of the size and
    // below the detector's stride.
    expect(suggestsTiling(616, 2464)).toBe(true);
  });

  it('renders the ratio rather than making the reader compute it', () => {
    renderField({ trainedWidth: 616, imageWidth: 2464 });

    expect(screen.getByRole('note')).toHaveTextContent(/616 px/);
    expect(screen.getByRole('note')).toHaveTextContent(/2464 px/);
    expect(screen.getByRole('note')).toHaveTextContent(/4\.0× smaller/);
  });

  it('is still shown once tiling is on, because it explains the result too', () => {
    renderField({ grid: { columns: 4, rows: 3, overlap: 0.2 }, trainedWidth: 616, imageWidth: 2464 });

    expect(screen.getByRole('note')).toBeInTheDocument();
    // But it stops telling you to do what you have already done.
    expect(screen.getByRole('note')).not.toHaveTextContent(/probably needed/);
  });
});

describe('what it will not do', () => {
  it('starts off', () => {
    // Never a property of the head: the same head over a close-up crop wants no grid.
    renderField({ trainedWidth: 616, imageWidth: 2464 });

    expect(screen.getByRole('checkbox')).not.toBeChecked();
  });

  it('does not turn itself on when the hint fires', () => {
    // The whole point. A control that enabled itself would make two runs of the same
    // configuration differ, which is worse than the empty result it would prevent.
    const { onChange } = renderField({ trainedWidth: 616, imageWidth: 2464 });

    expect(onChange).not.toHaveBeenCalled();
  });
});

describe('turning it on', () => {
  it('offers a grid that brings the frame back to about the trained size', async () => {
    // One click rather than arithmetic, for the case the hint just described.
    const { onChange, user } = renderField({ trainedWidth: 616, imageWidth: 2464 });

    await user.click(screen.getByRole('checkbox'));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ columns: 4, rows: 3 }));
  });

  it('falls back to a plain grid when it cannot know', async () => {
    const { onChange, user } = renderField();

    await user.click(screen.getByRole('checkbox'));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ columns: 3, rows: 2 }));
  });

  it('returns to the whole frame when switched off', async () => {
    const { onChange, user } = renderField({ grid: { columns: 4, rows: 3, overlap: 0.2 } });

    await user.click(screen.getByRole('checkbox'));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ columns: 1, rows: 1 }));
  });

  it('keeps the overlap across the toggle', async () => {
    // Doc 49's default is load-bearing — a grid differing from the training grid is a
    // different grid — so toggling must not quietly reset it.
    const { onChange, user } = renderField({ grid: { columns: 1, rows: 1, overlap: 0.35 } });

    await user.click(screen.getByRole('checkbox'));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ overlap: 0.35 }));
  });
});

describe('the grid inputs', () => {
  it('shows how many tiles that is', () => {
    renderField({ grid: { columns: 4, rows: 3, overlap: 0.2 } });

    expect(screen.getByText('12 tiles')).toBeInTheDocument();
  });

  it('are hidden while tiling is off', () => {
    renderField();

    expect(screen.queryByLabelText('Columns')).not.toBeInTheDocument();
  });

  it('keeps the last good value when the field is emptied mid-edit', async () => {
    const { onChange, user } = renderField({ grid: { columns: 4, rows: 3, overlap: 0.2 } });

    await user.clear(screen.getByLabelText('Columns'));

    expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ columns: 4 }));
  });
});

describe('suggestedGrid', () => {
  it('is the ratio, rounded', () => {
    expect(suggestedGrid(616, 2464)).toBe(4);
  });

  it('never suggests a 1x1, which would be no tiling at all', () => {
    expect(suggestedGrid(600, 700)).toBe(2);
  });

  it('is capped, because a 40x grid is a mistake not a request', () => {
    expect(suggestedGrid(100, 9000)).toBe(8);
  });
});

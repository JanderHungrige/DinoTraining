/**
 * The dataset-format guide (doc 48).
 *
 * The risk here is not markup, it is **drift**: this panel makes claims about
 * `coco_import.py`, and prose that quietly stops being true is worse than no prose. So the
 * tests pin the specific claims a reader would act on, and a backend test pins the filename
 * against the importer's own constant.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';

import { COCO_FILENAME, DATASET_FORMAT, SEARCH_DEPTH } from '../tabs/datasetFormat';
import { DatasetFormatPanel } from './DatasetFormatPanel';

describe('the disclosure', () => {
  it('starts closed', () => {
    render(<DatasetFormatPanel />);
    expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'false');
    expect(screen.queryByText(/The shape on disk/)).not.toBeInTheDocument();
  });

  it('opens on click', async () => {
    render(<DatasetFormatPanel />);
    await userEvent.setup().click(screen.getByRole('button'));
    expect(screen.getByRole('button')).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('The shape on disk')).toBeInTheDocument();
  });

  it('names the region it controls', async () => {
    // aria-expanded alone tells a screen reader something opened, not what.
    render(<DatasetFormatPanel />);
    await userEvent.setup().click(screen.getByRole('button'));
    const controls = screen.getByRole('button').getAttribute('aria-controls');
    expect(controls).toBeTruthy();
    expect(document.getElementById(controls as string)).toBeInTheDocument();
  });

  it('closes again', async () => {
    const user = userEvent.setup();
    render(<DatasetFormatPanel />);
    await user.click(screen.getByRole('button'));
    await user.click(screen.getByRole('button'));
    expect(screen.queryByText('The shape on disk')).not.toBeInTheDocument();
  });
});

describe('what it actually claims', () => {
  const text = DATASET_FORMAT.flatMap((s) => [...s.body, ...(s.tree ?? [])]).join(' ');

  it('names the annotation file the importer looks for', () => {
    expect(COCO_FILENAME).toBe('_annotations.coco.json');
    expect(text).toContain(COCO_FILENAME);
  });

  it('says the search is one level deep, matching find_coco_files', () => {
    // A user told "anywhere under here" will nest their splits two deep and get nothing,
    // with no error to explain it.
    expect(SEARCH_DEPTH).toBe(1);
    expect(text).toMatch(/one level/i);
  });

  it('gives the box convention explicitly, including what it is not', () => {
    // Every wrong-box import is one of these two confusions.
    expect(text).toMatch(/absolute pixels from the top-left/i);
    expect(text).toMatch(/x1, y1, x2, y2/);
    expect(text).toMatch(/YOLO/);
  });

  it('warns against filtering category 0', () => {
    // The bug doc 31 actually hit: blood's id 0 is the real class `platelets`.
    expect(text).toMatch(/platelets/);
  });

  it('says imported boxes are all positive', () => {
    expect(text).toMatch(/positive/i);
  });

  it('shows a directory tree, because the layout is the thing people get wrong', () => {
    expect(DATASET_FORMAT.some((s) => s.tree && s.tree.length > 0)).toBe(true);
  });

  it('tells the user what to check when it does not work', () => {
    expect(DATASET_FORMAT.some((s) => /will not import/i.test(s.heading))).toBe(true);
  });
});

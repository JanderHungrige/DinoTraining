/**
 * Choosing where the images come from (doc 50).
 *
 * A folder path and a dataset id are both "a string in a field", so the risk is ambiguity:
 * one input that took either would have to guess which the user meant, and a wrong guess
 * silently annotates the wrong pictures.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import type { DatasetInfo } from '../api/datasets';
import { ImageSourceField, type ImageSource } from './ImageSourceField';

vi.mock('../lib/dialog', () => ({
  hasNativeDialog: () => false,
  pickFolder: vi.fn(),
  pickImageFile: vi.fn(),
}));
vi.mock('../hooks/useFileDrop', () => ({
  useFileDrop: () => ({ dropping: false, available: false }),
}));

function dataset(id: string, name: string, images: number): DatasetInfo {
  return {
    id,
    name,
    created_at: '2026-01-01',
    prompt: null,
    copy_images: false,
    counts: { images, positive: 0, negative: 0, unclear: 0 },
  } as unknown as DatasetInfo;
}

const DATASETS = [dataset('d1', 'Chess', 289), dataset('d2', 'Empty', 0)];

function renderField(value: ImageSource = { kind: 'folder', folder: '' }) {
  const onChange = vi.fn();
  render(
    <ImageSourceField id="src" value={value} onChange={onChange} datasets={DATASETS} />,
  );
  return { onChange, user: userEvent.setup() };
}

describe('choosing a kind', () => {
  it('starts on a folder', () => {
    renderField();
    expect(screen.getByRole('radio', { name: /A folder/ })).toBeChecked();
    expect(screen.getByLabelText(/Image folder/)).toBeInTheDocument();
  });

  it('offers datasets that have images', async () => {
    const { onChange, user } = renderField();
    await user.click(screen.getByRole('radio', { name: /dataset you already have/ }));
    expect(onChange).toHaveBeenCalledWith({ kind: 'dataset', datasetId: 'd1' });
  });

  it('shows the dataset picker once chosen', () => {
    renderField({ kind: 'dataset', datasetId: 'd1' });
    expect(screen.getByLabelText('Dataset')).toHaveValue('d1');
    expect(screen.queryByLabelText(/Image folder/)).not.toBeInTheDocument();
  });

  it('does not offer an empty dataset', () => {
    // Choosing it would start a session with nothing in it and no explanation.
    renderField({ kind: 'dataset', datasetId: 'd1' });
    expect(screen.queryByRole('option', { name: /Empty/ })).not.toBeInTheDocument();
  });

  it('says so rather than offering an unusable choice when none have images', () => {
    const onChange = vi.fn();
    render(
      <ImageSourceField
        id="src"
        value={{ kind: 'folder', folder: '' }}
        onChange={onChange}
        datasets={[dataset('d2', 'Empty', 0)]}
      />,
    );
    expect(screen.getByRole('radio', { name: /none with images yet/ })).toBeDisabled();
  });
});

describe('reporting the choice', () => {
  it('reports a typed folder', async () => {
    const { onChange, user } = renderField();
    // One character: the field is controlled and the test does not feed `value` back,
    // so a second keystroke would report only the second character.
    await user.type(screen.getByLabelText(/Image folder/), '/');
    expect(onChange).toHaveBeenLastCalledWith({ kind: 'folder', folder: '/' });
  });

  it('reports a chosen dataset', async () => {
    const { onChange, user } = renderField({ kind: 'dataset', datasetId: 'd1' });
    await user.selectOptions(screen.getByLabelText('Dataset'), 'd1');
    expect(onChange).toHaveBeenCalledWith({ kind: 'dataset', datasetId: 'd1' });
  });

  it('shows the hint explaining what a dataset source does here', () => {
    // What picking a dataset *means* differs by tab, and a wrong guess about where
    // annotations land is the expensive kind of surprise.
    render(
      <ImageSourceField
        id="src"
        value={{ kind: 'dataset', datasetId: 'd1' }}
        onChange={vi.fn()}
        datasets={DATASETS}
        datasetHint="Its boxes load onto the canvas."
      />,
    );
    expect(screen.getByText('Its boxes load onto the canvas.')).toBeInTheDocument();
  });

  it('does not seed its selection from an async list', () => {
    // The classic bug: `useState(datasets[0]?.id)` runs before the fetch resolves, so the
    // select renders an option while state stays empty and submit is disabled forever.
    const onChange = vi.fn();
    const { rerender } = render(
      <ImageSourceField
        id="src"
        value={{ kind: 'dataset', datasetId: '' }}
        onChange={onChange}
        datasets={[]}
      />,
    );
    rerender(
      <ImageSourceField
        id="src"
        value={{ kind: 'dataset', datasetId: '' }}
        onChange={onChange}
        datasets={DATASETS}
      />,
    );
    expect(onChange).toHaveBeenCalledWith({ kind: 'dataset', datasetId: 'd1' });
  });
});

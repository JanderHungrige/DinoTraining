/**
 * Where the images come from: a folder, an image inside one, or a dataset (doc 50).
 *
 * `FolderField` (doc 46) answered the first two. The third exists because the app already
 * *has* the user's images once they have imported or generated a dataset, and making them
 * find the folder again — for data the store may have copied, so the folder they remember
 * is not where the images now are — is asking a question the app can answer itself.
 *
 * Two ways in, and the radio is what stops them being ambiguous. A folder path and a
 * dataset id are both "a string in a field", and one input that took either would have to
 * guess which the user meant.
 */

import { useEffect, useState, type JSX } from 'react';

import type { DatasetInfo } from '../api/datasets';
import { FolderField } from './FolderField';

export type ImageSource =
  | { readonly kind: 'folder'; readonly folder: string }
  | { readonly kind: 'dataset'; readonly datasetId: string };

export interface ImageSourceFieldProps {
  readonly value: ImageSource;
  readonly onChange: (source: ImageSource) => void;
  readonly datasets: readonly DatasetInfo[];
  readonly id: string;
  readonly placeholder?: string;
  readonly disabled?: boolean;
  readonly variant?: 'setup' | 'genpanel';
  /** Explains what picking a dataset does *here* — it differs by tab, and a wrong guess
   *  about where annotations land is the expensive kind of surprise. */
  readonly datasetHint?: string;
}

export function ImageSourceField({
  value,
  onChange,
  datasets,
  id,
  placeholder,
  disabled = false,
  variant = 'setup',
  datasetHint,
}: ImageSourceFieldProps): JSX.Element {
  // Only the user's override is stored; the shown value is derived. Seeding state from
  // `datasets` would strand the select empty whenever the list arrives after first render.
  const [override, setOverride] = useState('');
  const usable = datasets.filter((entry) => (entry.counts?.images ?? 0) > 0);
  // The `||` chain runs for *both* kinds on purpose. Reading `value.datasetId` alone
  // when the kind is already `dataset` looked right and was not: a source carrying an
  // empty id — which is what the very first switch produces, before the list has loaded —
  // would then never fall back, and the form would sit there pointing at no dataset while
  // rendering a select full of them.
  const chosen = value.kind === 'dataset' ? value.datasetId : override;
  const selected = chosen || usable[0]?.id || '';

  // A dataset that is chosen and then emptied elsewhere must not leave the form pointing
  // at nothing while still claiming to be ready.
  useEffect(() => {
    if (value.kind === 'dataset' && selected && value.datasetId !== selected) {
      onChange({ kind: 'dataset', datasetId: selected });
    }
  }, [value, selected, onChange]);

  return (
    <div className="srcfield">
      <fieldset className="srcfield__modes">
        <legend className="srcfield__legend">Images from</legend>
        <label>
          <input
            type="radio"
            name={`${id}-mode`}
            checked={value.kind === 'folder'}
            disabled={disabled}
            onChange={() => onChange({ kind: 'folder', folder: '' })}
          />
          <span>A folder</span>
        </label>
        <label>
          <input
            type="radio"
            name={`${id}-mode`}
            checked={value.kind === 'dataset'}
            disabled={disabled || usable.length === 0}
            onChange={() => onChange({ kind: 'dataset', datasetId: selected })}
          />
          <span>
            A dataset you already have
            {usable.length === 0 ? ' — none with images yet' : ''}
          </span>
        </label>
      </fieldset>

      {value.kind === 'folder' ? (
        <FolderField
          id={id}
          value={value.folder}
          onChange={(folder) => onChange({ kind: 'folder', folder })}
          {...(placeholder ? { placeholder } : {})}
          disabled={disabled}
          variant={variant}
        />
      ) : (
        <>
          <label
            className={variant === 'setup' ? 'setup__field setup__field--grow' : 'genpanel__field'}
            htmlFor={`${id}-dataset`}
          >
            Dataset
            <select
              id={`${id}-dataset`}
              value={selected}
              disabled={disabled}
              onChange={(event) => {
                setOverride(event.target.value);
                onChange({ kind: 'dataset', datasetId: event.target.value });
              }}
            >
              {usable.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.name} ({entry.counts?.images ?? 0} images)
                </option>
              ))}
            </select>
          </label>
          {datasetHint && <p className="srcfield__hint">{datasetHint}</p>}
        </>
      )}
    </div>
  );
}

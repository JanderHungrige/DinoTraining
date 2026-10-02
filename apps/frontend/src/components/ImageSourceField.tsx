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
import { useT } from '../i18n';
import { stillListed } from '../lib/persisted';
import { FolderField } from './FolderField';
import { RevealDatasetButton } from './RevealDatasetButton';
import { VideoSourceFields } from './VideoSourceFields';

/** Which frames of a video to decode (doc 73): every `stride`-th from `start`, `count` of them. */
export interface VideoRange {
  readonly start: number;
  readonly count: number;
  readonly stride: number;
}

export const DEFAULT_VIDEO_RANGE: VideoRange = Object.freeze({ start: 0, count: 120, stride: 1 });

export type ImageSource =
  | { readonly kind: 'folder'; readonly folder: string }
  | { readonly kind: 'dataset'; readonly datasetId: string }
  /** Doc 73, Dataset Generator only: decoded into the destination dataset first. */
  | { readonly kind: 'video'; readonly path: string; readonly range: VideoRange };

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
  /** Doc 73: offer a video file. Only the Dataset Generator can decode one. */
  readonly allowVideo?: boolean;
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
  allowVideo = false,
}: ImageSourceFieldProps): JSX.Element {
  const { t, tp } = useT();
  // Only the user's override is stored; the shown value is derived. Seeding state from
  // `datasets` would strand the select empty whenever the list arrives after first render.
  const [override, setOverride] = useState('');
  const usable = datasets.filter((entry) => (entry.counts?.images ?? 0) > 0);
  // The `||` chain runs for *both* kinds on purpose. Reading `value.datasetId` alone
  // when the kind is already `dataset` looked right and was not: a source carrying an
  // empty id — which is what the very first switch produces, before the list has loaded —
  // would then never fall back, and the form would sit there pointing at no dataset while
  // rendering a select full of them.
  // `stillListed` because the id may be remembered (doc 69) and deleted since. Once the
  // list arrives without it, the effect below moves the source onto the first usable one.
  const chosen = stillListed(
    value.kind === 'dataset' ? value.datasetId : override,
    usable.map((entry) => entry.id),
  );
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
        <legend className="srcfield__legend">{t('studio.source.legend')}</legend>
        <label>
          <input
            type="radio"
            name={`${id}-mode`}
            checked={value.kind === 'folder'}
            disabled={disabled}
            onChange={() => onChange({ kind: 'folder', folder: '' })}
          />
          <span>{t('studio.source.folder')}</span>
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
            {t('studio.source.dataset')}
            {usable.length === 0 ? ` — ${t('studio.source.noneWithImages')}` : ''}
          </span>
        </label>
        {allowVideo && (
          <label>
            <input
              type="radio"
              name={`${id}-mode`}
              checked={value.kind === 'video'}
              disabled={disabled}
              onChange={() => onChange({ kind: 'video', path: '', range: DEFAULT_VIDEO_RANGE })}
            />
            <span>{t('studio.source.video')}</span>
          </label>
        )}
      </fieldset>

      {value.kind === 'video' ? (
        <VideoSourceFields
          id={id}
          path={value.path}
          range={value.range}
          disabled={disabled}
          onChange={(path, range) => onChange({ kind: 'video', path, range })}
        />
      ) : value.kind === 'folder' ? (
        <>
          <FolderField
            id={id}
            value={value.folder}
            onChange={(folder) => onChange({ kind: 'folder', folder })}
            {...(placeholder ? { placeholder } : {})}
            disabled={disabled}
            variant={variant}
          />
          {/* Jan (2026-10-02) looked for the downloaded example with the folder button. */}
          {usable.length > 0 && <p className="srcfield__hint">{t('studio.source.folderHint')}</p>}
        </>
      ) : (
        <>
          <label
            className={variant === 'setup' ? 'setup__field setup__field--grow' : 'genpanel__field'}
            htmlFor={`${id}-dataset`}
          >
            {t('studio.choice.dataset')}
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
                  {tp('studio.choice.option', entry.counts?.images ?? 0, { name: entry.name })}
                </option>
              ))}
            </select>
          </label>
          <div className="srcfield__reveal">
            <RevealDatasetButton datasetId={selected} disabled={disabled} />
          </div>
          {datasetHint && <p className="srcfield__hint">{datasetHint}</p>}
        </>
      )}
    </div>
  );
}

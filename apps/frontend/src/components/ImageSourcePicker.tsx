/**
 * Pick the input: one image, or a folder of them.
 *
 * A text field first, a native dialog second. Under Tauri the dialog plugin gives real
 * pickers; in the `web` dev mode and in Wave 9 there is none, so the field is always
 * editable and it is the browse buttons that disappear — the rule Wave 1's
 * `SessionSetup` established.
 */

import { useEffect, useState, type FormEvent, type JSX } from 'react';

import { useFileDrop } from '../hooks/useFileDrop';
import type { DatasetInfo } from '../api/datasets';
import { hasNativeDialog, pickFolder, pickImageFile } from '../lib/dialog';

export interface ImageSourcePickerProps {
  readonly onPick: (path: string) => void;
  /** Picking a dataset instead of a path (doc 50). Omit both to keep the path-only form. */
  readonly datasets?: readonly DatasetInfo[];
  readonly datasetId?: string;
  readonly onPickDataset?: (datasetId: string) => void;
  /** The path currently loaded, if any. The field falls back to it until the user types. */
  readonly value?: string;
  readonly busy?: boolean;
}

export function ImageSourcePicker({
  onPick,
  datasets = [],
  datasetId = '',
  onPickDataset,
  value,
  busy = false,
}: ImageSourcePickerProps): JSX.Element {
  // Only the user's override is stored; the shown value is derived. Seeding state from
  // `value` would strand the field empty whenever the path arrives after first render.
  const [draft, setDraft] = useState<string | null>(null);
  const [hasPicker, setHasPicker] = useState(false);

  useEffect(() => {
    setHasPicker(hasNativeDialog());
  }, []);

  // No `folderOf` here: doc 17's source contract takes a single image *or* a folder and
  // returns the same shape either way, so a dropped file is already valid input.
  const drop = useFileDrop((paths) => {
    const first = paths[0];
    if (!first) return;
    setDraft(first);
    onPick(first);
  });

  const shown = draft ?? value ?? '';
  const usable = datasets.filter((entry) => (entry.counts?.images ?? 0) > 0);

  const submit = (event: FormEvent): void => {
    event.preventDefault();
    const trimmed = shown.trim();
    if (!trimmed) return;
    onPick(trimmed);
  };

  const browse = (pick: () => Promise<string | null>): void => {
    void pick().then((picked) => {
      if (!picked) return;
      setDraft(picked);
      onPick(picked);
    });
  };

  return (
    <form className="setup" onSubmit={submit}>
      <div className={`setup__row${drop.dropping ? ' setup__row--dropping' : ''}`}>
        <label className="setup__field setup__field--grow" htmlFor="source-path">
          {drop.dropping ? 'Drop to load it' : 'Image or folder'}
          <span className="setup__control">
            <input
              id="source-path"
              type="text"
              value={shown}
              placeholder="/Users/you/photos"
              // Never disabled while busy: typing the next path while the current one
              // loads is not a mistake to prevent. Only the submit is held back.
              onChange={(event) => setDraft(event.target.value)}
            />
            {hasPicker && (
              <>
                <button type="button" className="btn" onClick={() => browse(pickImageFile)}>
                  Image…
                </button>
                <button type="button" className="btn" onClick={() => browse(pickFolder)}>
                  Folder…
                </button>
              </>
            )}
            <button type="submit" className="btn btn--primary" disabled={busy}>
              Load
            </button>
          </span>
        </label>
      </div>
      {/* A second way in rather than a mode switch: the viewer is a place you dip into
          repeatedly, and making the user pick "folder or dataset" before every look would
          be a question asked far more often than its answer changes. */}
      {onPickDataset !== undefined && usable.length > 0 && (
        <div className="setup__row">
          <label className="setup__field setup__field--grow" htmlFor="source-dataset">
            …or a dataset you already have
            <select
              id="source-dataset"
              value={datasetId}
              disabled={busy}
              onChange={(event) => onPickDataset(event.target.value)}
            >
              <option value="">None</option>
              {usable.map((entry) => (
                <option key={entry.id} value={entry.id}>
                  {entry.name} ({entry.counts?.images ?? 0} images)
                </option>
              ))}
            </select>
          </label>
        </div>
      )}
      {drop.available && (
        <p className="fieldhint">Or drag an image or a folder onto this window.</p>
      )}
    </form>
  );
}

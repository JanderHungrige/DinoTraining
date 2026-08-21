/**
 * "Which folder of images?" — the field, its pickers, and its drop target (doc 46).
 *
 * The Dataset Generator had no picker at all: a bare text box the user was expected to
 * type an absolute path into, next to two tabs that offer **Image…** and **Folder…**
 * buttons. That is what "the dataset picker is not working" meant.
 *
 * Extracted rather than copied a third time, because one rule here is subtle and easy to
 * get wrong in a copy: **an image means the folder it is in.** A user who picks or drops
 * `photos/cat-07.jpg` is telling you where their photos are, not asking to process one
 * file — so `folderOf` is applied on *both* paths in, and the field can never end up
 * holding a file path that the backend will then reject.
 *
 * That is exactly why `ImageSourcePicker` does **not** use this: doc 17's viewer takes a
 * single image *or* a folder and means different things by each, so collapsing one into
 * the other there would break it.
 */

import { useEffect, useState, type JSX } from 'react';

import { useFileDrop } from '../hooks/useFileDrop';
import { hasNativeDialog, pickFolder, pickImageFile } from '../lib/dialog';
import { folderOf } from '../lib/dragDrop';
import { FieldHint } from './FieldHint';

export interface FolderFieldProps {
  readonly value: string;
  readonly onChange: (folder: string) => void;
  readonly id: string;
  readonly placeholder?: string;
  readonly required?: boolean;
  readonly disabled?: boolean;
  /** `setup` for the Annotation Studio's form, `genpanel` for the Dataset Generator's
   *  panel. The two surfaces have different layouts and neither should inherit the
   *  other's — but the *behaviour* below must not diverge again. */
  readonly variant?: 'setup' | 'genpanel';
}

export function FolderField({
  value,
  onChange,
  id,
  placeholder = '/Users/you/photos',
  required = false,
  disabled = false,
  variant = 'setup',
}: FolderFieldProps): JSX.Element {
  // Read in an effect, not at module scope: `hasNativeDialog` asks whether Tauri injected
  // its globals, and under Vite's SSR-shaped first render it has not yet.
  const [hasPicker, setHasPicker] = useState(false);
  useEffect(() => {
    setHasPicker(hasNativeDialog());
  }, []);

  const drop = useFileDrop((paths) => {
    const first = paths[0];
    if (first) onChange(folderOf(first));
  });

  const browse = (pick: () => Promise<string | null>): void => {
    void pick().then((picked) => {
      if (picked) onChange(folderOf(picked));
    });
  };

  const hintId = `${id}-hint`;

  return (
    <>
      <label
        className={
          variant === 'setup'
            ? `setup__field setup__field--grow${drop.dropping ? ' setup__field--dropping' : ''}`
            : 'genpanel__field'
        }
        htmlFor={id}
      >
        {drop.dropping ? 'Drop to use that folder' : 'Image folder'}
        <span className="setup__control">
          <input
            id={id}
            type="text"
            value={value}
            placeholder={placeholder}
            required={required}
            disabled={disabled}
            aria-describedby={drop.available ? hintId : undefined}
            onChange={(event) => onChange(event.target.value)}
          />
          {hasPicker && (
            <>
              {/* Picking an image is the common case — people know where a photo is more
                  readily than they know the folder's name — so it comes first. */}
              <button
                type="button"
                className="btn"
                disabled={disabled}
                onClick={() => browse(pickImageFile)}
              >
                Image…
              </button>
              <button
                type="button"
                className="btn"
                disabled={disabled}
                onClick={() => browse(pickFolder)}
              >
                Folder…
              </button>
            </>
          )}
        </span>
      </label>
      {drop.available && (
        <FieldHint id={hintId}>
          Pick an image and its folder is used. You can also drag a folder — or any image
          inside it — onto this window.
        </FieldHint>
      )}
    </>
  );
}

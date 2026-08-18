/**
 * Pick the input: one image, or a folder of them.
 *
 * A text field first, a native dialog second. Under Tauri the dialog plugin gives real
 * pickers; in the `web` dev mode and in Wave 6 there is none, so the field is always
 * editable and it is the browse buttons that disappear — the rule Wave 1's
 * `SessionSetup` established.
 */

import { useEffect, useState, type FormEvent, type JSX } from 'react';

import { hasNativeDialog, pickFolder, pickImageFile } from '../lib/dialog';

export interface ImageSourcePickerProps {
  readonly onPick: (path: string) => void;
  /** The path currently loaded, if any. The field falls back to it until the user types. */
  readonly value?: string;
  readonly busy?: boolean;
}

export function ImageSourcePicker({
  onPick,
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

  const shown = draft ?? value ?? '';

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
      <div className="setup__row">
        <label className="setup__field setup__field--grow" htmlFor="source-path">
          Image or folder
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
    </form>
  );
}

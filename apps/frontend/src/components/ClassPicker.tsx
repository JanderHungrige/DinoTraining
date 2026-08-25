/**
 * Choose a box's class, or make one to choose (doc 60).
 *
 * Replaces the free-text field doc 47 put in each review row. That field worked for a box
 * you had just drawn and knew the name of; it had no memory of the last thirty boxes, no
 * way to show what classes a dataset already has, and no way for a class to exist at all
 * before something was labelled with it.
 *
 * **A native `<select>`, not a combobox.** Keyboard behaviour, type-ahead, mobile
 * behaviour and an accessible name per row all come for free, and a hand-rolled listbox
 * would have to rebuild every one of them. `New class…` is a sentinel option whose value
 * cannot collide with a real class, because a class name is trimmed and non-empty.
 *
 * The create field replaces the select in place rather than opening a dialog: creating a
 * class is a small thing done mid-review, and a modal would take the image off screen to
 * type one word.
 */

import { useEffect, useRef, useState, type JSX } from 'react';

/** Sentinel option values. Neither can be a class name: one is empty and the other has a
 *  leading space, which `normalise` trims away server-side and this component trims too. */
const UNNAMED = '';
const NEW_CLASS = ' new';

export interface ClassPickerProps {
  /** The class this box carries, or '' for none. */
  readonly value: string;
  /** Every class that can be chosen, already sorted and de-duplicated. */
  readonly options: readonly string[];
  readonly onChange: (name: string) => void;
  /** Create a class. Resolves to the name as stored, or null if it could not be created —
   *  the stored spelling may differ in case from what was typed. */
  readonly onCreate: (name: string) => Promise<string | null>;
  /** Rename this class across the current image. Omitted where renaming has no meaning. */
  readonly onRename?: (from: string, to: string) => void;
  /** For the accessible name — "Class of box 3" reads better than a bare "Class". */
  readonly label: string;
  readonly disabled?: boolean;
}

type Editing = { readonly kind: 'new' } | { readonly kind: 'rename'; readonly from: string };

export function ClassPicker({
  value,
  options,
  onChange,
  onCreate,
  onRename,
  label,
  disabled = false,
}: ClassPickerProps): JSX.Element {
  const [editing, setEditing] = useState<Editing | null>(null);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const fieldRef = useRef<HTMLInputElement | null>(null);

  // Focus follows the field appearing, or the control is on screen with nobody in it and
  // the keyboard is still on the select that is no longer there.
  useEffect(() => {
    if (editing) fieldRef.current?.focus();
  }, [editing]);

  // A class the box carries but the vocabulary has not got — a proposal whose class was
  // never saved, or one deleted from the vocabulary while boxes still carry it. Without
  // this the select would show the wrong option, because a value with no matching option
  // renders as whichever one happens to be first.
  const known = options.some((name) => name.toLowerCase() === value.toLowerCase());
  const listed = known || value === '' ? options : [value, ...options];

  const commit = async (): Promise<void> => {
    const trimmed = draft.trim();
    if (!trimmed || !editing) {
      setEditing(null);
      return;
    }
    if (editing.kind === 'rename') {
      onRename?.(editing.from, trimmed);
      setEditing(null);
      setDraft('');
      return;
    }
    setBusy(true);
    const created = await onCreate(trimmed);
    setBusy(false);
    // Only select on success. Selecting a class the server refused would show one that
    // does not exist and lose it on the next load.
    if (created !== null) onChange(created);
    setEditing(null);
    setDraft('');
  };

  if (editing) {
    const renaming = editing.kind === 'rename';
    return (
      <span className="classpicker classpicker--editing">
        <input
          ref={fieldRef}
          className="classpicker__field"
          type="text"
          value={draft}
          maxLength={100}
          placeholder={renaming ? editing.from : 'New class'}
          aria-label={
            renaming ? `Rename ${editing.from}, ${label}` : `New class for ${label}`
          }
          disabled={busy}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            // Enter commits, Escape abandons. Blur does neither: tabbing past a control
            // must not create a class, which is why there is an explicit button.
            if (event.key === 'Enter') {
              event.preventDefault();
              void commit();
            }
            if (event.key === 'Escape') {
              event.preventDefault();
              setEditing(null);
              setDraft('');
            }
          }}
        />
        <button
          type="button"
          className="btn btn--small"
          disabled={busy || draft.trim() === ''}
          onClick={() => void commit()}
        >
          {renaming ? 'Rename' : 'Add'}
        </button>
        <button
          type="button"
          className="btn btn--small"
          disabled={busy}
          onClick={() => {
            setEditing(null);
            setDraft('');
          }}
        >
          Cancel
        </button>
      </span>
    );
  }

  return (
    <span className="classpicker">
      <select
        className="classpicker__select"
        value={value}
        aria-label={label}
        disabled={disabled}
        onChange={(event) => {
          if (event.target.value === NEW_CLASS) {
            setDraft('');
            setEditing({ kind: 'new' });
            return;
          }
          onChange(event.target.value);
        }}
      >
        <option value={UNNAMED}>— unnamed —</option>
        {listed.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
        <option value={NEW_CLASS}>New class…</option>
      </select>

      {/* Renaming is offered only when there is a class to rename, and only where the
          caller can act on it. A proposal run names thirty boxes the same thing and the
          correction is one decision, not thirty. */}
      {onRename && value !== '' && (
        <button
          type="button"
          className="classpicker__rename"
          title={`Rename ${value} on every box in this image`}
          /* The row is part of the name. A class on several boxes means several of these
             buttons, and identical accessible names give a screen-reader user a list of
             indistinguishable controls — the scope is the same for all of them, but the
             control they are on is not. */
          aria-label={`Rename ${value} on every box in this image, ${label}`}
          disabled={disabled}
          onClick={() => {
            setDraft(value);
            setEditing({ kind: 'rename', from: value });
          }}
        >
          <span aria-hidden="true">✎</span>
        </button>
      )}
    </span>
  );
}

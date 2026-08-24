/**
 * The native file dialogs, in one place.
 *
 * Only present inside the Tauri webview. In the `web` dev mode — and in Wave 9 — there is
 * no dialog at all, so every caller must stay usable without one: the path field is
 * always editable and the browse buttons are what disappear, never the field.
 *
 * Wave 1 had this inline in `SessionSetup`; this is the second caller, which is the point
 * at which one implementation earns its keep.
 */

/** Image extensions the backend will accept — mirrors `IMAGE_SUFFIXES` in `app/ml/images.py`. */
const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'bmp', 'webp', 'tif', 'tiff', 'gif'];

/** True when a native picker is available. Callers hide their browse buttons when false. */
export function hasNativeDialog(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

async function open(options: Record<string, unknown>): Promise<string | null> {
  if (!hasNativeDialog()) return null;
  try {
    const { open: openDialog } = await import('@tauri-apps/plugin-dialog');
    const selected = await openDialog(options);
    return typeof selected === 'string' ? selected : null;
  } catch {
    // A cancelled or unavailable dialog is not an error the user needs to see — they
    // can still type the path.
    return null;
  }
}

export function pickFolder(): Promise<string | null> {
  return open({ directory: true, multiple: false });
}

export function pickImageFile(): Promise<string | null> {
  return open({
    directory: false,
    multiple: false,
    filters: [{ name: 'Images', extensions: IMAGE_EXTENSIONS }],
  });
}


/** Show a folder in Finder / Explorer / the Linux file manager (doc 59).
 *
 *  Same shape as the pickers above and for the same reason: it exists only inside the
 *  Tauri webview, so every caller must stay usable without it — the button disappears,
 *  nothing else changes.
 *
 *  `revealItemInDir` rather than `openPath`: revealing selects the item in a *new* file
 *  manager window, while opening a directory can reuse an existing window the user was
 *  looking at something else in.
 */
export async function revealFolder(path: string): Promise<void> {
  if (!hasNativeDialog()) return;
  const { revealItemInDir } = await import('@tauri-apps/plugin-opener');
  await revealItemInDir(path);
}

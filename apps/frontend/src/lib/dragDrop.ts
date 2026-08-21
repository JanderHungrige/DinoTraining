/**
 * File drops from the desktop, in one place (doc 40).
 *
 * **Tauri only, on purpose.** Tauri's webview emits `{type: 'drop', paths: string[]}` —
 * real filesystem paths, which feed doc 17's path-based contract with no conversion. A
 * browser drop yields `File` objects with no path at all, and the backend has nothing to
 * open. Rather than add an upload endpoint — a second input contract, the one doc 17
 * deliberately avoided, plus a temp-file lifecycle — the drop target is simply not offered
 * where it cannot work. Same shape as `hasNativeDialog`: the affordance disappears, the
 * path field never does.
 *
 * The event is **window-level**, not per-element: Tauri reports a drop on the webview, not
 * on whatever was under the cursor. Only one tab is mounted at a time, so exactly one
 * listener exists and the active tab is the one that gets it.
 */

/** Extensions the backend will open — mirrors `IMAGE_SUFFIXES` in `app/ml/images.py`. */
const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'bmp', 'webp', 'tif', 'tiff', 'gif'];

export interface FileDropHandlers {
  readonly onEnter?: () => void;
  readonly onLeave?: () => void;
  readonly onDrop: (paths: readonly string[]) => void;
}

/** True when file drops carry a real path. False in a browser, including `web` dev mode. */
export function hasFileDrop(): boolean {
  return typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window;
}

/**
 * Subscribe to desktop file drops. Returns an unsubscribe function.
 *
 * Resolves to a no-op outside Tauri rather than throwing, so callers do not each need the
 * capability check before wiring up.
 */
export async function listenForFileDrop(
  handlers: FileDropHandlers,
): Promise<() => void> {
  if (!hasFileDrop()) return () => {};
  try {
    const { getCurrentWebview } = await import('@tauri-apps/api/webview');
    return await getCurrentWebview().onDragDropEvent((event) => {
      const payload = event.payload;
      if (payload.type === 'enter') handlers.onEnter?.();
      else if (payload.type === 'leave') handlers.onLeave?.();
      else if (payload.type === 'drop') {
        handlers.onLeave?.();
        handlers.onDrop(payload.paths);
      }
    });
  } catch {
    // An unavailable webview API is not something the user can act on — they can still
    // type the path, which is why the field is never disabled.
    return () => {};
  }
}

/**
 * The folder a dropped path stands for.
 *
 * The Studio and the Generator take a **folder**, but people drop the images they can see
 * rather than the folder containing them. Dropping one image and being told "not a folder"
 * is a worse answer than doing the obvious thing.
 *
 * Decided by extension rather than by asking the filesystem: the frontend has no `stat`,
 * and a round trip to find out would make a drop feel slow. A directory that happens to be
 * named `photos.png` is mis-handled — and is not a thing that exists.
 */
export function folderOf(path: string): string {
  const separator = path.includes('\\') && !path.includes('/') ? '\\' : '/';
  const name = path.slice(path.lastIndexOf(separator) + 1);
  const dot = name.lastIndexOf('.');
  if (dot <= 0) return path;

  const extension = name.slice(dot + 1).toLowerCase();
  if (!IMAGE_EXTENSIONS.includes(extension)) return path;

  const parent = path.slice(0, path.lastIndexOf(separator));
  // A file at the filesystem root has an empty parent; the root itself is the answer.
  return parent || separator;
}

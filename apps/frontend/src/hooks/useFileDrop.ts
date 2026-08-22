/**
 * React binding for desktop file drops (doc 40).
 *
 * Returns whether something is currently hovering, so a target can say "let go here"
 * rather than accepting a drop with no visible acknowledgement.
 */

import { useEffect, useRef, useState } from 'react';

import { hasFileDrop, listenForFileDrop } from '../lib/dragDrop';

export interface FileDropState {
  /** True while files are over the window. Always false where drops are unavailable. */
  readonly dropping: boolean;
  /** False in a browser — callers hide the drop affordance rather than lying about it. */
  readonly available: boolean;
}

export function useFileDrop(onDrop: (paths: readonly string[]) => void): FileDropState {
  const [dropping, setDropping] = useState(false);

  // The subscription must not be torn down and rebuilt every time the caller passes a
  // fresh closure — that would drop the listener mid-drag. The ref holds the latest
  // handler; the effect runs once.
  const handler = useRef(onDrop);
  handler.current = onDrop;

  useEffect(() => {
    let unlisten: (() => void) | null = null;
    let cancelled = false;

    void listenForFileDrop({
      onEnter: () => setDropping(true),
      onLeave: () => setDropping(false),
      onDrop: (paths) => handler.current(paths),
    }).then((stop) => {
      // Unmounted before the listener resolved: stop it immediately, or it outlives the
      // component and fires into a dead handler.
      if (cancelled) stop();
      else unlisten = stop;
    });

    return () => {
      cancelled = true;
      unlisten?.();
    };
  }, []);

  return { dropping, available: hasFileDrop() };
}

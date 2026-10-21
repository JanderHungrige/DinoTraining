/**
 * Keeps its last height while its content is swapped for a short placeholder (2026-10-21).
 *
 * The Studio replaced the whole canvas and list with one "Loading…" line between pictures.
 * The page got shorter by the picture's height, the browser pulled the scroll position up,
 * and it stayed there: every new picture jumped the window back up (Jan). Held at its last
 * height, the page keeps its length and the scroll position stays.
 */

import { useLayoutEffect, useRef, useState, type JSX, type ReactNode } from 'react';

export function KeepHeight({ holding, children }: { readonly holding: boolean; readonly children: ReactNode }): JSX.Element {
  const box = useRef<HTMLDivElement | null>(null);
  const [held, setHeld] = useState(0);

  useLayoutEffect(() => {
    // Measured only while the real content shows; that height is what a placeholder keeps.
    if (!holding && box.current) setHeld(box.current.offsetHeight);
  });

  return (
    <div ref={box} className="keepheight" style={holding && held ? { minHeight: `${held}px` } : undefined}>
      {children}
    </div>
  );
}

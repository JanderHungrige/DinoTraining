/**
 * Where this copy came from (doc 156), from the shell's `app_edition`.
 *
 * `store`: the Microsoft Store's MSIX, which Windows uninstalls and updates on its own.
 * `installer`: the EXE / DMG / AppImage from the download site. `dev`: a debug build.
 * `web`: no shell at all (the web dev mode).
 */

import { useEffect, useState } from 'react';

import { hasNativeDialog } from './dialog';

export type Edition = 'store' | 'installer' | 'dev' | 'web';

let asked: Promise<Edition> | null = null;

export function appEdition(): Promise<Edition> {
  if (!hasNativeDialog()) return Promise.resolve('web');
  asked ??= import('@tauri-apps/api/core')
    .then(({ invoke }) => invoke<Edition>('app_edition'))
    .catch((error: unknown) => {
      // An older shell without the command is an installer build.
      console.warn('app_edition unavailable', error);
      return 'installer' as const;
    });
  return asked;
}

/** `null` until the shell has answered. */
export function useEdition(): Edition | null {
  const [edition, setEdition] = useState<Edition | null>(null);
  useEffect(() => {
    let live = true;
    void appEdition().then((answer) => {
      if (live) setEdition(answer);
    });
    return () => {
      live = false;
    };
  }, []);
  return edition;
}

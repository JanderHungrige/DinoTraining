/**
 * Doc 144: every n minutes while the app is open, export what changed. The interval lives
 * here, where the user works, not in a backend timer: nobody working, nothing new.
 */

import { useEffect, useState } from 'react';

import { getExportSettings, runExports, SETTINGS_EVENT } from '../api/exports';

const MINUTE_MS = 60_000;
const RETRY_MS = 30_000;

export function useAutoExport(): void {
  const [minutes, setMinutes] = useState(0);

  useEffect(() => {
    let retry: number | undefined;
    const load = (): void => {
      getExportSettings()
        .then((settings) => setMinutes(settings.every_minutes))
        .catch((error: unknown) => {
          // The backend may still be starting (first run): ask again shortly.
          console.warn('Export settings unavailable', error);
          retry = window.setTimeout(load, RETRY_MS);
        });
    };
    load();
    window.addEventListener(SETTINGS_EVENT, load);
    return () => {
      window.clearTimeout(retry);
      window.removeEventListener(SETTINGS_EVENT, load);
    };
  }, []);

  useEffect(() => {
    if (minutes <= 0) return undefined;
    const timer = window.setInterval(() => {
      // A run already going answers "busy"; the next tick tries again.
      runExports('interval', false).catch((error: unknown) => console.warn('Interval export failed', error));
    }, minutes * MINUTE_MS);
    return () => window.clearInterval(timer);
  }, [minutes]);
}

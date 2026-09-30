/**
 * Shows the setup screen instead of the app until the Python environment is installed
 * (doc 127). Outside the desktop shell, and in a checkout, there is nothing to install
 * and the app renders at once — synchronously, so nothing else changes for the web mode
 * or the tests.
 */

import { useCallback, useEffect, useState, type JSX, type ReactNode } from 'react';

import { SetupScreen } from './SetupScreen';
import { inShell, setupStatus, type Machine, type Variant } from './shell';

type Gate = { readonly kind: 'checking' } | { readonly kind: 'app' } | { readonly kind: 'setup'; readonly machine: Machine; readonly auto: Variant | null; readonly update: Variant | null };

export function SetupGate({ children }: { readonly children: ReactNode }): JSX.Element | null {
  const [gate, setGate] = useState<Gate>(() => (inShell() ? { kind: 'checking' } : { kind: 'app' }));

  useEffect(() => {
    if (gate.kind !== 'checking') return;
    let cancelled = false;
    setupStatus()
      .then((status) => {
        if (cancelled) return;
        setGate(
          status.needed && status.machine ? { kind: 'setup', machine: status.machine, auto: status.auto, update: status.update } : { kind: 'app' },
        );
      })
      .catch((error: unknown) => {
        // A shell without the command (an older build) has nothing to set up either.
        console.error('setup_status failed; showing the app', error);
        if (!cancelled) setGate({ kind: 'app' });
      });
    return () => {
      cancelled = true;
    };
  }, [gate.kind]);

  const done = useCallback(() => setGate({ kind: 'app' }), []);

  if (gate.kind === 'checking') return null;
  if (gate.kind === 'setup') return <SetupScreen machine={gate.machine} auto={gate.auto} update={gate.update} onDone={done} />;
  return <>{children}</>;
}

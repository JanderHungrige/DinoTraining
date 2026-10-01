/**
 * Doc 128: the setup screen over the app while PyTorch is exchanged. The backend is
 * stopped meanwhile, so nothing behind the overlay would work anyway.
 */

import type { JSX } from 'react';

import { SetupScreen } from './SetupScreen';
import { switchVariant, type Machine, type Variant } from './shell';

interface Props {
  readonly machine: Machine;
  readonly variant: Variant;
  /** Switched, or gave up after a rollback: the backend answers again either way. */
  readonly onClose: () => void;
}

export function SwitchOverlay({ machine, variant, onClose }: Props): JSX.Element {
  return (
    <div className="firstrun-overlay" role="dialog" aria-modal="true">
      <SetupScreen machine={machine} auto={variant} onDone={onClose} switching={{ run: switchVariant, onBack: onClose }} />
    </div>
  );
}

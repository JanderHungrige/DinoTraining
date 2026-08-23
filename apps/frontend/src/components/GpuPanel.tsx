/**
 * "You have a GPU this build cannot use" (doc 57).
 *
 * Wave 8 ships a CPU-only sidecar so the installer stays around half a gigabyte rather
 * than the 2.5 GB a CUDA torch wheel costs on Windows (doc 56). That trade is only
 * acceptable if the app *says* when it is costing the user something — silence there
 * means training crawls and nothing explains why.
 *
 * **It renders only in the one actionable state.** Not when there is no NVIDIA hardware
 * (most machines, and a standing "no GPU found" notice is noise), and not when the build
 * already uses CUDA (nothing to do). A panel that is always there is one nobody reads.
 */

import type { JSX } from 'react';

import type { AcceleratorInfo } from '../api/models';

export interface GpuPanelProps {
  readonly accelerator: AcceleratorInfo | null;
  /** Size of the CUDA sidecar for this platform, in MB. */
  readonly downloadMb: number;
  readonly onDownload?: () => void;
  readonly busy?: boolean;
}

function gib(memoryMb: number): string {
  return `${(memoryMb / 1024).toFixed(0)} GB`;
}

export function GpuPanel({
  accelerator,
  downloadMb,
  onDownload,
  busy = false,
}: GpuPanelProps): JSX.Element | null {
  if (accelerator === null) return null;

  // A driver that is installed and not answering is a different problem from having no
  // GPU, and it needs a different fix — so it gets said rather than folded into silence.
  if (accelerator.driver_error) {
    return (
      <section className="gpupanel gpupanel--warn" aria-labelledby="gpu-title">
        <h3 className="gpupanel__title" id="gpu-title">
          NVIDIA driver not responding
        </h3>
        <p className="gpupanel__lead">{accelerator.summary}</p>
        <p className="gpupanel__foot">
          Reinstalling or updating the driver usually fixes this. Until it answers, this
          app cannot tell whether a GPU is present.
        </p>
      </section>
    );
  }

  if (!accelerator.upgrade_available) return null;

  return (
    <section className="gpupanel" aria-labelledby="gpu-title">
      <h3 className="gpupanel__title" id="gpu-title">
        <span aria-hidden="true">⚡</span> Your GPU is not being used
      </h3>
      <p className="gpupanel__lead">{accelerator.summary}</p>

      <ul className="gpupanel__list">
        {accelerator.nvidia.map((gpu) => (
          <li key={`${gpu.name}-${gpu.driver_version}`}>
            <strong>{gpu.name}</strong> · {gib(gpu.memory_mb)} · driver {gpu.driver_version}
          </li>
        ))}
      </ul>

      <p className="gpupanel__foot">
        The installer ships a CPU build so it stays small. GPU support is a separate
        download of about <strong>{(downloadMb / 1024).toFixed(1)} GB</strong> — it is
        large because it carries NVIDIA's CUDA runtime, not because the app is. Training
        and inference typically run several times faster on it.
      </p>

      {onDownload && (
        <button
          type="button"
          className="btn btn--primary btn--small"
          disabled={busy}
          onClick={onDownload}
        >
          {busy ? 'Downloading…' : `Download GPU support (${(downloadMb / 1024).toFixed(1)} GB)`}
        </button>
      )}
    </section>
  );
}

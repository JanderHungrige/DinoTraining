/**
 * The GPU panel (docs 57 and 128): whether this machine's GPU is used, and the switch.
 *
 * **It renders only when there is something to know or do.** Not on a machine without
 * NVIDIA hardware (most machines, and a Mac, whose PyTorch always carries MPS). In the
 * packaged app it switches the installed PyTorch between CPU and GPU (doc 128); in a
 * development checkout it says how to install the GPU build, since the checkout's
 * environment is the developer's.
 */

import type { JSX } from 'react';

import type { AcceleratorInfo } from '../api/models';
import { useT } from '../i18n';
import { formatGb } from '../setup/MachineSummary';
import { CUDA_VERSION, type RuntimeStatus, type Variant } from '../setup/shell';

export interface GpuPanelProps {
  readonly accelerator: AcceleratorInfo | null;
  /** Doc 128: null outside the packaged app. */
  readonly runtime?: RuntimeStatus | null;
  readonly onSwitch?: (variant: Variant) => void;
}

function gib(memoryMb: number): string {
  return `${(memoryMb / 1024).toFixed(0)} GB`;
}

function GpuList({ accelerator }: { readonly accelerator: AcceleratorInfo }): JSX.Element {
  const { t } = useT();
  return (
    <ul className="gpupanel__list">
      {accelerator.nvidia.map((gpu) => (
        <li key={`${gpu.name}-${gpu.driver_version}`}>
          <strong>{gpu.name}</strong> · {gib(gpu.memory_mb)} · {t('admin.gpu.driver', { version: gpu.driver_version })}
        </li>
      ))}
    </ul>
  );
}

function Panel({ title, warn = false, children }: { readonly title: string; readonly warn?: boolean; readonly children: React.ReactNode }): JSX.Element {
  return (
    <section className={warn ? 'gpupanel gpupanel--warn' : 'gpupanel'} aria-labelledby="gpu-title">
      <h3 className="gpupanel__title" id="gpu-title">
        {title}
      </h3>
      {children}
    </section>
  );
}

/** The packaged app: the installed variant decides what the panel offers (doc 128). */
function Packaged({ accelerator, runtime, onSwitch }: { readonly accelerator: AcceleratorInfo; readonly runtime: RuntimeStatus; readonly onSwitch?: ((variant: Variant) => void) | undefined }): JSX.Element | null {
  const { t, lang } = useT();
  const installedCuda = runtime.variant ? CUDA_VERSION[runtime.variant] : null;
  const back = onSwitch && (
    <button type="button" className="btn btn--small" onClick={() => onSwitch('cpu')}>
      {t('admin.gpu.backToCpu')}
    </button>
  );

  if (installedCuda && accelerator.device === 'cuda') {
    const name = accelerator.nvidia[0]?.name ?? 'NVIDIA';
    return (
      <Panel title={t('admin.gpu.inUse', { name, cuda: installedCuda })}>
        <p className="gpupanel__foot">{t('admin.gpu.switchNote')}</p>
        {back}
      </Panel>
    );
  }
  if (installedCuda) {
    return (
      <Panel title={t('admin.gpu.notUsedTitle', { cuda: installedCuda })} warn>
        <p className="gpupanel__lead">{accelerator.summary}</p>
        {back}
      </Panel>
    );
  }

  const gpu = runtime.machine.choices.find((choice) => CUDA_VERSION[choice.variant] !== null);
  const note = runtime.machine.note;
  if (!gpu) {
    if (note?.kind !== 'driver_too_old') return null;
    return (
      <Panel title={t('admin.gpu.title')} warn>
        <p className="gpupanel__lead">{t('setup.note.driverTooOld', { driver: note.driver, needed: String(note.needed) })}</p>
      </Panel>
    );
  }
  return (
    <Panel title={`⚡ ${t('admin.gpu.title')}`}>
      <p className="gpupanel__lead">{accelerator.summary}</p>
      <GpuList accelerator={accelerator} />
      <p className="gpupanel__foot">{t('admin.gpu.switchNote')}</p>
      {onSwitch && (
        <button type="button" className="btn btn--primary btn--small" onClick={() => onSwitch(gpu.variant)}>
          {t('admin.gpu.use', { cuda: CUDA_VERSION[gpu.variant] ?? '', gb: formatGb(gpu.download_gb, lang) })}
        </button>
      )}
    </Panel>
  );
}

export function GpuPanel({ accelerator, runtime = null, onSwitch }: GpuPanelProps): JSX.Element | null {
  const { t } = useT();
  if (accelerator === null) return null;

  // A driver that is installed and not answering is a different problem from having no
  // GPU, and it needs a different fix — so it gets said rather than folded into silence.
  if (accelerator.driver_error) {
    return (
      <Panel title={t('admin.gpu.driverTitle')} warn>
        <p className="gpupanel__lead">{accelerator.summary}</p>
        <p className="gpupanel__foot">{t('admin.gpu.driverFoot')}</p>
      </Panel>
    );
  }
  if (runtime) return <Packaged accelerator={accelerator} runtime={runtime} onSwitch={onSwitch} />;
  if (!accelerator.upgrade_available) return null;

  return (
    <Panel title={`⚡ ${t('admin.gpu.title')}`}>
      <p className="gpupanel__lead">{accelerator.summary}</p>
      <GpuList accelerator={accelerator} />
      <p className="gpupanel__foot">{t('admin.gpu.devFoot')}</p>
    </Panel>
  );
}

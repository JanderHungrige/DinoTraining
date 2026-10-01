/** Wave 1 — Admin / Models: system status and the model download manager. */

import { useEffect, useState, type JSX } from 'react';

import {
  FAMILY_ORDER,
  type ModelFamily,
  type ModelInfo,
} from '../api/models';
import { AnnotatorReadiness } from '../components/AnnotatorReadiness';
import { HeadCatalogPanel } from '../components/HeadCatalogPanel';
import { StarterSetPanel } from '../components/StarterSetPanel';
import { DistributionNotice } from '../components/DistributionNotice';
import { GpuPanel } from '../components/GpuPanel';
import { ModelCard } from '../components/ModelCard';
import { getAccelerator, type AcceleratorInfo } from '../api/models';
import { SwitchOverlay } from '../setup/SwitchOverlay';
import { runtimeStatus, type RuntimeStatus, type Variant } from '../setup/shell';

import { TokenPanel } from '../components/TokenPanel';
import { AppearancePanel } from '../components/AppearancePanel';
import { useModels } from '../hooks/useModels';
import { useTrainerOptions } from '../hooks/useTrainerOptions';
import { useT, type Key } from '../i18n';

/** Headings per family; the English text is `FAMILY_LABELS` in api/models.ts. */
const FAMILY_KEYS: Readonly<Record<ModelFamily, Key>> = Object.freeze({
  'grounding-dino': 'admin.family.groundingDino',
  'rf-detr': 'admin.family.rfDetr',
  dinov2: 'admin.family.dinov2',
  dinov3: 'admin.family.dinov3',
  sam2: 'admin.family.sam2',
  sam3: 'admin.family.sam3',
  'depth-anything': 'admin.family.depthAnything',
});

function SystemPanel({
  device,
  cacheDir,
  tokenPresent,
  freeDiskMb,
}: {
  readonly device: string;
  readonly cacheDir: string;
  readonly tokenPresent: boolean;
  readonly freeDiskMb: number;
}): JSX.Element {
  const { t } = useT();
  return (
    <dl className="sysinfo">
      <div className="sysinfo__item">
        <dt>{t('admin.system.device')}</dt>
        <dd>{device.toUpperCase()}</dd>
      </div>
      <div className="sysinfo__item">
        <dt>{t('admin.system.freeDisk')}</dt>
        <dd>{(freeDiskMb / 1024).toFixed(1)} GB</dd>
      </div>
      <div className="sysinfo__item">
        <dt>{t('admin.system.token')}</dt>
        <dd>{tokenPresent ? t('admin.system.tokenSet') : t('admin.system.tokenUnset')}</dd>
      </div>
      <div className="sysinfo__item sysinfo__item--wide">
        <dt>{t('admin.system.cache')}</dt>
        <dd>
          <code>{cacheDir}</code>
        </dd>
      </div>
    </dl>
  );
}

export function AdminTab(): JSX.Element {
  const { models, system, jobs, loading, error, busy, download, remove, refresh } = useModels();
  const { t } = useT();

  // Its own effect and its own failure: a driver probe that errors should cost the GPU
  // panel, not the model list beneath it.
  const [accelerator, setAccelerator] = useState<AcceleratorInfo | null>(null);
  // Doc 128: bumped after a CPU ⇄ GPU switch, so the panel re-reads what the new
  // backend runs on — the device check the switch ends with.
  const [probe, setProbe] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    void getAccelerator(controller.signal)
      .then(setAccelerator)
      .catch(() => setAccelerator(null));
    return () => controller.abort();
  }, [probe]);
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null);
  useEffect(() => {
    let cancelled = false;
    runtimeStatus()
      .then((status) => !cancelled && setRuntime(status))
      .catch((failure: unknown) => {
        console.error('runtime_status failed; the GPU switch stays hidden', failure);
      });
    return () => {
      cancelled = true;
    };
  }, [probe]);
  const [switchTo, setSwitchTo] = useState<Variant | null>(null);
  const switched = (): void => {
    setSwitchTo(null);
    setProbe((n) => n + 1);
    void refresh();
  };
  // Null backbone: the head-catalogue panel does its own per-backbone filtering, and
  // asking for verdicts here would tie the whole tab to one selection.
  const { backbones, headTypes } = useTrainerOptions(null);

  const byFamily = (family: ModelFamily): ModelInfo[] =>
    models.filter((model) => model.family === family);

  return (
    <section className="admin">
      <h2 className="admin__title">{t('admin.models.title')}</h2>

      {system && (
        <SystemPanel
          device={system.device}
          cacheDir={system.cache_dir}
          tokenPresent={system.hf_token_present}
          freeDiskMb={system.free_disk_mb}
        />
      )}
      {/* One switch, in the header — this only says where it is. */}
      <p className="admin__groupnote">{t('admin.system.languageNote')}</p>

      {/* Above the model list, because it is about what is already downloaded and the
          remove buttons are just below. */}
      {/* Above the model list and below the system panel: it is about this machine,
          like the panel above it, and it appears only when there is something to do. */}
      <GpuPanel accelerator={accelerator} runtime={runtime} onSwitch={setSwitchTo} />
      {switchTo && runtime && <SwitchOverlay machine={runtime.machine} variant={switchTo} onClose={switched} />}

      <DistributionNotice models={models} />

      <TokenPanel />
      <AppearancePanel />

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
      )}

      {/* First, and above the catalogue: someone on a fresh install should not have to
          work out which five of fifteen models matter before anything works. */}
      {!loading && (
        <StarterSetPanel models={models} jobs={jobs} onDownload={download} />
      )}

      {loading ? (
        <p role="status">{t('admin.models.loading')}</p>
      ) : (
        FAMILY_ORDER.map((family) => {
          const entries = byFamily(family);
          if (entries.length === 0) return null;
          return (
            <section key={family} className="admin__group">
              <h3 className="admin__grouptitle">{t(FAMILY_KEYS[family])}</h3>
              <div className="admin__grid">
                {entries.map((model) => (
                  <ModelCard
                    key={model.id}
                    model={model}
                    job={jobs[model.id]}
                    busy={busy[model.id] ?? false}
                    onDownload={download}
                    onRemove={remove}
                  />
                ))}
              </div>
            </section>
          );
        })
      )}

      {/* After the models, because it explains how some of them combine — and it is
          keyed on the job map so installing a part re-reads readiness. */}
      <AnnotatorReadiness refreshKey={Object.keys(jobs).length} />

      <HeadCatalogPanel backbones={backbones} headTypes={headTypes} />
    </section>
  );
}

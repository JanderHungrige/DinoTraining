/** Wave 1 — Admin / Models: system status and the model download manager. */

import { useEffect, useState, type JSX } from 'react';

import {
  FAMILY_LABELS,
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

/** The CUDA sidecar's download size. Stated here rather than fetched: it is a property
 *  of the *release*, not of the running app, and the app cannot know it before asking
 *  for it. Update alongside the release. */
const CUDA_SIDECAR_MB = 2400;
import { TokenPanel } from '../components/TokenPanel';
import { useModels } from '../hooks/useModels';
import { useTrainerOptions } from '../hooks/useTrainerOptions';

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
  return (
    <dl className="sysinfo">
      <div className="sysinfo__item">
        <dt>Compute device</dt>
        <dd>{device.toUpperCase()}</dd>
      </div>
      <div className="sysinfo__item">
        <dt>Free disk</dt>
        <dd>{(freeDiskMb / 1024).toFixed(1)} GB</dd>
      </div>
      <div className="sysinfo__item">
        <dt>HuggingFace token</dt>
        <dd>{tokenPresent ? 'Configured' : 'Not set — gated models unavailable'}</dd>
      </div>
      <div className="sysinfo__item sysinfo__item--wide">
        <dt>Model cache</dt>
        <dd>
          <code>{cacheDir}</code>
        </dd>
      </div>
    </dl>
  );
}

export function AdminTab(): JSX.Element {
  const { models, system, jobs, loading, error, busy, download, remove } = useModels();

  // Its own effect and its own failure: a driver probe that errors should cost the GPU
  // panel, not the model list beneath it.
  const [accelerator, setAccelerator] = useState<AcceleratorInfo | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void getAccelerator(controller.signal)
      .then(setAccelerator)
      .catch(() => setAccelerator(null));
    return () => controller.abort();
  }, []);
  // Null backbone: the head-catalogue panel does its own per-backbone filtering, and
  // asking for verdicts here would tie the whole tab to one selection.
  const { backbones, headTypes } = useTrainerOptions(null);

  const byFamily = (family: ModelFamily): ModelInfo[] =>
    models.filter((model) => model.family === family);

  return (
    <section className="admin">
      <h2 className="admin__title">Admin / Models</h2>

      {system && (
        <SystemPanel
          device={system.device}
          cacheDir={system.cache_dir}
          tokenPresent={system.hf_token_present}
          freeDiskMb={system.free_disk_mb}
        />
      )}

      {/* Above the model list, because it is about what is already downloaded and the
          remove buttons are just below. */}
      {/* Above the model list and below the system panel: it is about this machine,
          like the panel above it, and it appears only when there is something to do. */}
      <GpuPanel accelerator={accelerator} downloadMb={CUDA_SIDECAR_MB} />

      <DistributionNotice models={models} />

      <TokenPanel />

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
        <p role="status">Loading model catalogue…</p>
      ) : (
        FAMILY_ORDER.map((family) => {
          const entries = byFamily(family);
          if (entries.length === 0) return null;
          return (
            <section key={family} className="admin__group">
              <h3 className="admin__grouptitle">{FAMILY_LABELS[family]}</h3>
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

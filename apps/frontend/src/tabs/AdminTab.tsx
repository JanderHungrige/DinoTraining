/** Wave 1 — Admin / Models: system status and the model download manager. */

import type { JSX } from 'react';

import { FAMILY_LABELS, type ModelFamily, type ModelInfo } from '../api/models';
import { HeadCatalogPanel } from '../components/HeadCatalogPanel';
import { ModelCard } from '../components/ModelCard';
import { useModels } from '../hooks/useModels';
import { useTrainerOptions } from '../hooks/useTrainerOptions';

const FAMILY_ORDER: readonly ModelFamily[] = ['grounding-dino', 'dinov2', 'dinov3'];

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

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
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

      <HeadCatalogPanel backbones={backbones} headTypes={headTypes} />
    </section>
  );
}

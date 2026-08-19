/**
 * Choose what the generator runs: a folder, a backbone, and one trained head.
 *
 * The selection rule from CLAUDE.md applies to all three fields. Backbones and heads
 * arrive asynchronously, so `useState(list[0]?.id ?? '')` would run once, before the fetch
 * resolves, and leave the state at `''` while the control renders its first option anyway
 * — the form looks filled in and Start stays disabled forever. Only the user's *override*
 * is stored; the effective value is derived.
 */

import { useEffect, useState, type JSX } from 'react';

import type { BackboneInfo } from '../api/backbones';
import { listHeadInstances, type HeadInstanceInfo } from '../api/headInstances';
import { installedOnly, useTrainerOptions } from '../hooks/useTrainerOptions';
import { ExpertHeadPicker } from './ExpertHeadPicker';
import type { GeneratorConfig } from '../hooks/useGeneratorSession';

export interface GeneratorSetupProps {
  readonly onStart: (config: GeneratorConfig) => void;
}

const DEFAULT_THRESHOLD = 0.3;

export function GeneratorSetup({ onStart }: GeneratorSetupProps): JSX.Element {
  const [folder, setFolder] = useState('');
  const [backboneOverride, setBackboneOverride] = useState('');
  const [headOverride, setHeadOverride] = useState('');
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);

  const [heads, setHeads] = useState<readonly HeadInstanceInfo[]>([]);
  const [loadingHeads, setLoadingHeads] = useState(true);

  const { backbones, loading: loadingBackbones, error } = useTrainerOptions(null);
  const installed: readonly BackboneInfo[] = installedOnly(backbones);

  // Derived, never seeded: the first installed backbone until the user picks another.
  const backboneId = backboneOverride || installed[0]?.id || '';

  useEffect(() => {
    const controller = new AbortController();
    listHeadInstances({}, controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setHeads(found);
      })
      .catch(() => {
        /* the picker renders its own empty state */
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoadingHeads(false);
      });
    return () => controller.abort();
  }, []);

  const eligible = heads.filter(
    (head) => head.render_hint === 'boxes' && head.backbone_id === backboneId,
  );
  const instanceId = headOverride || eligible[0]?.id || '';

  const ready = folder.trim().length > 0 && backboneId !== '' && instanceId !== '';

  return (
    <form
      className="genpanel"
      onSubmit={(event) => {
        event.preventDefault();
        if (!ready) return;
        onStart({
          folder: folder.trim(),
          backboneId,
          instanceId,
          scoreThreshold: threshold,
        });
      }}
    >
      <label className="genpanel__field">
        <span>Image folder</span>
        <input
          type="text"
          value={folder}
          placeholder="/Users/you/new-photos"
          onChange={(event) => setFolder(event.target.value)}
        />
      </label>

      <label className="genpanel__field">
        <span>Backbone</span>
        <select
          value={backboneId}
          disabled={loadingBackbones || installed.length === 0}
          onChange={(event) => {
            setBackboneOverride(event.target.value);
            // The head list is filtered by backbone, so a stale override would keep a
            // head selected that the new backbone cannot run.
            setHeadOverride('');
          }}
        >
          {installed.map((backbone) => (
            <option key={backbone.id} value={backbone.id}>
              {backbone.id}
            </option>
          ))}
        </select>
      </label>

      <ExpertHeadPicker
        heads={heads}
        backboneId={backboneId}
        selectedId={instanceId}
        onSelect={setHeadOverride}
        loading={loadingHeads}
      />

      <label className="genpanel__field">
        <span>Score threshold — {threshold.toFixed(2)}</span>
        <input
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={threshold}
          onChange={(event) => setThreshold(Number(event.target.value))}
        />
      </label>

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
      )}

      <button type="submit" className="btn btn--primary" disabled={!ready}>
        Start generating
      </button>
    </form>
  );
}

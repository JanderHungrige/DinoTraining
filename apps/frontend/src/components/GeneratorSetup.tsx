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
import {
  GeneratorDestination,
  destinationReady,
  resolveDataset,
} from './GeneratorDestination';
import { GROUNDED_SAM, listAnnotators, type AnnotatorInfo } from '../api/annotators';
import type { GeneratorConfig } from '../hooks/useGeneratorSession';

export interface GeneratorSetupProps {
  readonly onStart: (config: GeneratorConfig) => void;
}

const DEFAULT_THRESHOLD = 0.3;

type Mode = 'expert' | 'masks';

export function GeneratorSetup({ onStart }: GeneratorSetupProps): JSX.Element {
  const [folder, setFolder] = useState('');
  const [mode, setMode] = useState<Mode>('expert');
  const [concept, setConcept] = useState('');
  const [datasetOverride, setDatasetOverride] = useState('');
  const [newName, setNewName] = useState('');
  const [starting, setStarting] = useState(false);
  const [annotators, setAnnotators] = useState<readonly AnnotatorInfo[]>([]);
  const [annotatorOverride, setAnnotatorOverride] = useState('');
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
    listAnnotators(controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setAnnotators(found);
      })
      .catch(() => {
        /* the mask mode falls back to the ungated default */
      });
    return () => controller.abort();
  }, []);

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

  // Only annotators whose models are actually downloaded. SAM 3 is 3.2 GB behind a
  // manual approval, so it appears here the moment it is installed and not before —
  // the catalogue in the admin tab is where a user goes to get it.
  const readyAnnotators = annotators.filter((annotator) => annotator.ready);
  const annotatorId =
    annotatorOverride || readyAnnotators[0]?.id || GROUNDED_SAM;

  const eligible = heads.filter(
    (head) => head.render_hint === 'boxes' && head.backbone_id === backboneId,
  );
  const instanceId = headOverride || eligible[0]?.id || '';

  const datasetId = datasetOverride;

  const ready =
    destinationReady(datasetId, newName) &&
    folder.trim().length > 0 &&
    (mode === 'expert'
      ? backboneId !== '' && instanceId !== ''
      : concept.trim().length > 0);

  return (
    <form
      className="genpanel"
      onSubmit={(event) => {
        event.preventDefault();
        if (!ready || starting) return;
        setStarting(true);
        void resolveDataset(datasetId, newName)
          .then((resolvedId) =>
            onStart(
              mode === 'expert'
                ? {
                    kind: 'expert' as const,
                    datasetId: resolvedId,
                    folder: folder.trim(),
                    backboneId,
                    instanceId,
                    scoreThreshold: threshold,
                  }
                : {
                    kind: 'masks' as const,
                    datasetId: resolvedId,
                    folder: folder.trim(),
                    annotatorId,
                    concept: concept.trim(),
                    scoreThreshold: threshold,
                  },
            ),
          )
          .finally(() => setStarting(false));
      }}
    >
      <GeneratorDestination
        datasetId={datasetId}
        newName={newName}
        onSelect={setDatasetOverride}
        onNameChange={setNewName}
      />

      <fieldset className="genpanel__modes">
        <legend>What proposes the annotations</legend>
        <label className="genpanel__mode">
          <input
            type="radio"
            name="generator-mode"
            checked={mode === 'expert'}
            onChange={() => setMode('expert')}
          />
          <span>A head you trained — proposes boxes</span>
        </label>
        <label className="genpanel__mode">
          <input
            type="radio"
            name="generator-mode"
            checked={mode === 'masks'}
            onChange={() => setMode('masks')}
          />
          <span>Grounded SAM — type a concept, get masks</span>
        </label>
      </fieldset>

      <label className="genpanel__field">
        <span>Image folder</span>
        <input
          type="text"
          value={folder}
          placeholder="/Users/you/new-photos"
          onChange={(event) => setFolder(event.target.value)}
        />
      </label>

      {mode === 'masks' && (
        <div className="genpanel__group">
          {readyAnnotators.length > 1 && (
            <label className="genpanel__field">
              <span>Annotator</span>
              <select
                value={annotatorId}
                onChange={(event) => setAnnotatorOverride(event.target.value)}
              >
                {readyAnnotators.map((annotator) => (
                  <option key={annotator.id} value={annotator.id}>
                    {annotator.name}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="genpanel__field">
            <span>Concept</span>
            <input
              type="text"
              value={concept}
              placeholder="a bolt. a nut."
              onChange={(event) => setConcept(event.target.value)}
            />
          </label>
          {/* Outside the label on purpose: text inside a <label> joins the field's
              accessible name, so this paragraph would be read out with every focus. */}
          <p className="genpanel__hint">
            {annotatorId === GROUNDED_SAM
              ? 'Grounding DINO finds each phrase and SAM 2.1 turns it into a mask. Nothing here is gated — no token, no account.'
              : (annotators.find((a) => a.id === annotatorId)?.description ?? '')}
          </p>
        </div>
      )}

      {mode === 'expert' && (
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

      )}

      {mode === 'expert' && (
        <ExpertHeadPicker
          heads={heads}
          backboneId={backboneId}
          selectedId={instanceId}
          onSelect={setHeadOverride}
          loading={loadingHeads}
        />
      )}

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

      <button type="submit" className="btn btn--primary" disabled={!ready || starting}>
        {starting ? 'Starting…' : 'Start generating'}
      </button>
    </form>
  );
}

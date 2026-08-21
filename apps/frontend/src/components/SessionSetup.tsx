/**
 * Session setup: pick a folder, pick or create a dataset, then choose **what proposes** —
 * a text prompt for Grounding DINO, or a head you trained (doc 33).
 *
 * The two modes are **exclusive**, and the form shows only the fields of the chosen one.
 * Hiding the prompt is not enough on its own: the user has to be able to see which mode
 * they are in, because the two produce differently-sourced proposals that land in the same
 * canvas. The radio group is the answer, and the union in `SessionConfig` is what stops a
 * caller from constructing both at once.
 *
 * The folder is a text field with an optional native picker. Under Tauri the dialog
 * plugin gives a real picker; in a browser (the `web` dev mode, and Wave 9) there is
 * none, so the field is always editable rather than being disabled without one.
 */

import { useEffect, useState, type FormEvent, type JSX } from 'react';

import { DEFAULT_BOX_THRESHOLD, DEFAULT_TEXT_THRESHOLD } from '../api/annotate';
import { createDataset, listDatasets, type DatasetInfo } from '../api/datasets';
import { listFoundations, type FoundationInfo } from '../api/foundation';
import { listHeadInstances, type HeadInstanceInfo } from '../api/headInstances';
import type { SessionConfig } from '../hooks/useAnnotationSession';
import { hasNativeDialog, pickFolder } from '../lib/dialog';
import { folderOf } from '../lib/dragDrop';
import { useFileDrop } from '../hooks/useFileDrop';
import { ExpertHeadPicker } from './ExpertHeadPicker';
import { FieldHint } from './FieldHint';
import { FoundationPicker } from './FoundationPicker';
import { ProposalModePicker, type ProposalMode } from './ProposalModePicker';
import { GROUNDING_DINO_HINT, headModeHint } from './promptGuidance';

/** Matches the Dataset Generator's default, and the only backbone a head can be run on. */
const BACKBONE_ID = 'dinov2-small';

export interface SessionSetupProps {
  readonly onStart: (config: SessionConfig) => void;
  readonly disabled?: boolean;
}

export function SessionSetup({ onStart, disabled = false }: SessionSetupProps): JSX.Element {
  const [folder, setFolder] = useState('');
  // Drop an image and you mean its folder — see `folderOf`. Only the first path is used:
  // this field holds one folder, and silently picking among several would be a guess.
  const drop = useFileDrop((paths) => {
    const first = paths[0];
    if (first) setFolder(folderOf(first));
  });
  const [mode, setMode] = useState<ProposalMode>('prompt');
  const [foundations, setFoundations] = useState<readonly FoundationInfo[]>([]);
  const [foundationOverride, setFoundationOverride] = useState('');
  const [prompt, setPrompt] = useState('');
  const [heads, setHeads] = useState<readonly HeadInstanceInfo[]>([]);
  const [loadingHeads, setLoadingHeads] = useState(true);
  // Only the user's override is stored; the effective head falls back to the first
  // compatible one. Seeding useState from an async fetch leaves it '' forever — the
  // form looks filled in and the submit button never enables. See CLAUDE.md.
  const [headOverride, setHeadOverride] = useState('');
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const [datasetId, setDatasetId] = useState('');
  const [newName, setNewName] = useState('');
  const [boxThreshold, setBoxThreshold] = useState(DEFAULT_BOX_THRESHOLD);
  const [error, setError] = useState<string | null>(null);
  const [hasPicker, setHasPicker] = useState(false);

  useEffect(() => {
    setHasPicker(hasNativeDialog());
    void listDatasets()
      .then(setDatasets)
      .catch(() => setError('Could not load datasets.'));
    void listHeadInstances()
      .then(setHeads)
      .catch(() => setHeads([]))
      .finally(() => setLoadingHeads(false));
    // Non-fatal: the other two modes still work if the catalogue is unhappy.
    void listFoundations()
      .then(setFoundations)
      .catch(() => setFoundations([]));
  }, []);

  // Derived, never seeded into state — the fetch resolves after the first render.
  const annotatable = heads.filter(
    (head) => head.render_hint === 'boxes' && head.backbone_id === BACKBONE_ID,
  );
  const selectedHead = headOverride || annotatable[0]?.id || '';
  // Derived, never seeded — the same rule, for the same reason.
  const usableDetectors = foundations.filter(
    (entry) => entry.render_hint === 'boxes' && entry.installed,
  );
  const selectedDetector = foundationOverride || usableDetectors[0]?.id || '';

  const handleSubmit = async (event: FormEvent): Promise<void> => {
    event.preventDefault();
    setError(null);

    if (mode === 'head' && !selectedHead) {
      setError('No head can propose boxes yet — train a detection head first.');
      return;
    }

    if (mode === 'foundation' && !selectedDetector) {
      setError('No general detector is installed — get one in Admin / Models.');
      return;
    }

    let targetId = datasetId;
    if (!targetId) {
      if (!newName.trim()) {
        setError('Choose an existing dataset or name a new one.');
        return;
      }
      try {
        const created = await createDataset(newName.trim(), prompt || null);
        targetId = created.id;
        setDatasets((current) => [created, ...current]);
        setDatasetId(created.id);
      } catch {
        setError('Could not create the dataset.');
        return;
      }
    }

    onStart({
      folder: folder.trim(),
      datasetId: targetId,
      source:
        mode === 'foundation'
          ? {
              kind: 'foundation',
              foundationId: selectedDetector,
              scoreThreshold: boxThreshold,
            }
          : mode === 'head'
          ? {
              kind: 'head',
              backboneId: BACKBONE_ID,
              instanceId: selectedHead,
              scoreThreshold: boxThreshold,
            }
          : {
              kind: 'prompt',
              prompt: prompt.trim(),
              boxThreshold,
              textThreshold: DEFAULT_TEXT_THRESHOLD,
            },
    });
  };

  return (
    <form className="setup" onSubmit={(event) => void handleSubmit(event)}>
      <div className={`setup__row${drop.dropping ? ' setup__row--dropping' : ''}`}>
        <label className="setup__field setup__field--grow" htmlFor="folder">
          {drop.dropping ? 'Drop to use that folder' : 'Image folder'}
          <span className="setup__control">
            <input
              id="folder"
              type="text"
              value={folder}
              placeholder="/Users/you/photos"
              required
              onChange={(event) => setFolder(event.target.value)}
            />
            {hasPicker && (
              <button
                type="button"
                className="btn"
                onClick={() => void pickFolder().then((picked) => picked && setFolder(picked))}
              >
                Browse…
              </button>
            )}
          </span>
        </label>
      </div>
      {drop.available && (
        <FieldHint id="folder-hint">
          Or drag a folder — or any image inside it — onto this window.
        </FieldHint>
      )}

      <div className="setup__row">
        <label className="setup__field" htmlFor="dataset">
          Dataset
          <select
            id="dataset"
            value={datasetId}
            onChange={(event) => setDatasetId(event.target.value)}
          >
            <option value="">Create a new one…</option>
            {datasets.map((dataset) => (
              <option key={dataset.id} value={dataset.id}>
                {dataset.name} ({dataset.counts.images} images)
              </option>
            ))}
          </select>
        </label>

        {!datasetId && (
          <label className="setup__field" htmlFor="newname">
            New dataset name
            <input
              id="newname"
              type="text"
              value={newName}
              placeholder="Cats"
              onChange={(event) => setNewName(event.target.value)}
            />
          </label>
        )}
      </div>

      <ProposalModePicker mode={mode} onChange={setMode} />

      {mode === 'head' && (
        <FieldHint id="studio-mode-hint">
          {headModeHint(annotatable.find((head) => head.id === selectedHead)?.class_names ?? [])}
        </FieldHint>
      )}

      {mode === 'foundation' && (
        <FoundationPicker
          foundations={foundations}
          selectedId={selectedDetector}
          onSelect={setFoundationOverride}
          legend="Detector"
          groupName="studio-detector"
        />
      )}

      {mode === 'head' && (
        <ExpertHeadPicker
          heads={heads}
          backboneId={BACKBONE_ID}
          selectedId={selectedHead}
          onSelect={setHeadOverride}
          loading={loadingHeads}
          legend="Annotate with"
          groupName="studio-head"
        />
      )}

      <div className="setup__row">
        {mode === 'prompt' && (
          <label className="setup__field setup__field--grow" htmlFor="prompt">
            Prompt
            <input
              id="prompt"
              type="text"
              value={prompt}
              placeholder="a cat. a dog."
              aria-describedby="prompt-hint"
              required
              onChange={(event) => setPrompt(event.target.value)}
            />
          </label>
        )}

        <label className="setup__field" htmlFor="boxthreshold">
          {mode === 'prompt' ? 'Box threshold' : 'Score threshold'}{' '}
          <span className="setup__value">{boxThreshold.toFixed(2)}</span>
          <input
            id="boxthreshold"
            type="range"
            min={0.05}
            max={0.95}
            step={0.05}
            value={boxThreshold}
            onChange={(event) => setBoxThreshold(Number(event.target.value))}
          />
        </label>
      </div>

      {mode === 'prompt' && <FieldHint id="prompt-hint">{GROUNDING_DINO_HINT}</FieldHint>}

      {error && (
        <p className="admin__error" role="alert">
          {error}
        </p>
      )}

      <button type="submit" className="btn btn--primary" disabled={disabled}>
        Start annotating
      </button>
    </form>
  );
}

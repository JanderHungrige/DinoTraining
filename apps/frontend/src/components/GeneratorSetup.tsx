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

import { listDatasets, type DatasetInfo } from '../api/datasets';

import type { BackboneInfo } from '../api/backbones';
import { listHeadInstances, type HeadInstanceInfo } from '../api/headInstances';
import { installedOnly, useTrainerOptions } from '../hooks/useTrainerOptions';
import { ExpertHeadPicker } from './ExpertHeadPicker';
import { ImageSourceField, type ImageSource } from './ImageSourceField';
import { FoundationPicker } from './FoundationPicker';
import { GeneratorModePicker, type GeneratorMode } from './GeneratorModePicker';
import { MaskSourceFields } from './MaskSourceFields';
import { listFoundations, proposesBoxes, type FoundationInfo } from '../api/foundation';
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

export function GeneratorSetup({ onStart }: GeneratorSetupProps): JSX.Element {
  const [source, setSource] = useState<ImageSource>({ kind: 'folder', folder: '' });
  // Loaded here as well as in `GeneratorDestination`: the source picker offers datasets
  // to *read* and the destination offers them to *write*, and the two lists answer
  // different questions — one filters to datasets that have images.
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    void listDatasets(controller.signal)
      .then(setDatasets)
      .catch(() => setDatasets([]));
    return () => controller.abort();
  }, []);
  // The default is unchanged. A general detector leads the *list*, which is where
  // discoverability lives, but selecting it by default would drop someone who has trained
  // heads and no detector installed onto an empty state telling them to visit Admin.
  // Deriving the default from what is installed would mean seeding state from an async
  // fetch, which is this project's most-repeated bug. See doc 42's known issues.
  const [mode, setMode] = useState<GeneratorMode>('expert');
  const [foundations, setFoundations] = useState<readonly FoundationInfo[]>([]);
  const [detectorOverride, setDetectorOverride] = useState('');
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
    // Non-fatal: the other two modes still work if the catalogue is unhappy.
    listFoundations(controller.signal)
      .then((found) => {
        if (!controller.signal.aborted) setFoundations(found);
      })
      .catch(() => undefined);
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

  // Derived, never seeded from an async fetch — the rule this project keeps relearning.
  //
  // `proposesBoxes`, not `render_hint === 'boxes'`, because that is what `FoundationPicker`
  // renders by and the two lists disagreeing is a bug on its own: SAM 3 appeared in the
  // picker and was absent from *this* list, so the default selection and the ready gate
  // were reasoning about a different set of models than the user could see.
  const usableDetectors = foundations.filter(
    (entry) => proposesBoxes(entry) && entry.installed,
  );
  const selectedDetector = detectorOverride || usableDetectors[0]?.id || '';
  // Whether the chosen detector needs a prompt. Read off the catalogue entry, never from
  // its id (doc 66) — Grounding DINO, Grounded SAM and SAM 3 are all prompted and share no
  // id pattern at all.
  const detectorNeedsConcept =
    usableDetectors.find((entry) => entry.id === selectedDetector)?.takes_concept === true;

  // Only annotators whose models are actually downloaded. SAM 3 is 3.2 GB behind a
  // manual approval, so it appears here the moment it is installed and not before —
  // the catalogue in the admin tab is where a user goes to get it.
  const readyAnnotators = annotators.filter((annotator) => annotator.ready);
  const annotatorId =
    annotatorOverride || readyAnnotators[0]?.id || GROUNDED_SAM;

  // From the catalogue row, not from the id. Grounded SAM is three rows now (doc 27) and
  // an id comparison would have given the two new ones SAM 3's single-concept wording
  // while the pipeline behind them happily accepted several phrases.
  const promptStyle =
    readyAnnotators.find((annotator) => annotator.id === annotatorId)?.prompt_style ??
    'phrases';

  const eligible = heads.filter(
    (head) => head.render_hint === 'boxes' && head.backbone_id === backboneId,
  );
  const instanceId = headOverride || eligible[0]?.id || '';

  const datasetId = datasetOverride;

  const ready =
    destinationReady(datasetId, newName) &&
    (source.kind === 'dataset' ? source.datasetId !== '' : source.folder.trim() !== '') &&
    (mode === 'foundation'
      ? selectedDetector !== '' && (!detectorNeedsConcept || concept.trim().length > 0)
      : mode === 'expert'
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
              mode === 'foundation'
                ? {
                    kind: 'foundation' as const,
                    datasetId: resolvedId,
                    images: source,
                    foundationId: selectedDetector,
                    concept: detectorNeedsConcept ? concept.trim() : '',
                    scoreThreshold: threshold,
                  }
                : mode === 'expert'
                ? {
                    kind: 'expert' as const,
                    datasetId: resolvedId,
                    images: source,
                    backboneId,
                    instanceId,
                    scoreThreshold: threshold,
                  }
                : {
                    kind: 'masks' as const,
                    datasetId: resolvedId,
                    images: source,
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

      <GeneratorModePicker mode={mode} onChange={setMode} />

      <ImageSourceField
        id="gen-folder"
        value={source}
        onChange={setSource}
        datasets={datasets}
        placeholder="/Users/you/new-photos"
        variant="genpanel"
        datasetHint="Its images are re-annotated into whichever dataset you choose below — the source is only where the pictures come from."
      />

      <MaskSourceFields
        mode={mode}
        annotators={readyAnnotators}
        annotatorId={annotatorId}
        onAnnotatorChange={setAnnotatorOverride}
        concept={concept}
        onConceptChange={setConcept}
        promptStyle={promptStyle}
      />

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

      {mode === 'foundation' && (
        <FoundationPicker
          foundations={foundations}
          selectedId={selectedDetector}
          onSelect={setDetectorOverride}
          legend="Detector"
          groupName="generator-detector"
          concept={concept}
          onConceptChange={setConcept}
        />
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

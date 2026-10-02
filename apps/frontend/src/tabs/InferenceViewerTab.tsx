/**
 * Wave 3 — Inference Viewer.
 *
 * Assembles the wave: an input source (doc 17), a head selection run through one shared
 * backbone pass (doc 18), the two panes (doc 19), and the overlays (doc 20).
 *
 * This file knows nothing about what a head produces. It hands predictions to
 * `renderOverlayFor`, which dispatches on `render_hint`.
 */

import { useEffect, useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { listDatasets, type DatasetInfo } from '../api/datasets';
import { HeadRunPanel } from '../components/HeadRunPanel';
import { ImageSourcePicker } from '../components/ImageSourcePicker';
import { SideBySideViewer } from '../components/SideBySideViewer';
import { AnnotationViewToggle } from '../components/AnnotationViewToggle';
import { SequencePanel } from '../components/SequencePanel';
import { renderOverlayFor } from '../components/overlays/registry';
import { ScoreNote, ScoreSlider } from '../components/ScoreThreshold';
import { aboveScore, DEFAULT_MIN_SCORE } from '../lib/scoreFilter';
import { DEFAULT_VIEW, type AnnotationView } from '../types/annotationView';
import { useHeadRun } from '../hooks/useHeadRun';
import { useT } from '../i18n';
import { useImageSource } from '../hooks/useImageSource';
import { usePersistentState } from '../hooks/usePersistentState';
import {
  isAnnotationView,
  isNullable,
  isNumber,
  isOneOf,
  isString,
  stillListed,
} from '../lib/persisted';

/** The two things this tab does. Same shape as the Training tab's switch. */
const MODES = [
  {
    id: 'image' as const,
    name: 'run.viewer.modeImageName',
    hint: 'run.viewer.modeImageHint',
  },
  {
    id: 'video' as const,
    name: 'run.viewer.modeVideoName',
    hint: 'run.viewer.modeVideoHint',
  },
] as const;

type ViewerMode = (typeof MODES)[number]['id'];

const isViewerMode = isOneOf<ViewerMode>(MODES.map((entry) => entry.id));

export function InferenceViewerTab(): JSX.Element {
  const { t, tp } = useT();
  // Explicit rather than inferred from what the path turns out to be. The player used to
  // appear on its own whenever a folder probed as playable, which meant a folder could not
  // be stepped through image by image without the player also being there — two surfaces
  // for one source, neither of them chosen.
  // Doc 69: the mode, path, dataset and view are remembered across tab switches.
  const [mode, setMode] = usePersistentState<ViewerMode>('viewer.mode', 'image', isViewerMode);
  const [path, setPath] = usePersistentState<string | null>(
    'viewer.path',
    null,
    isNullable(isString),
  );
  // Read from the image itself rather than from any prediction: the tiling hint has to be
  // available *before* a run, which is exactly when there is no prediction to ask.
  const [imageWidth, setImageWidth] = useState<number | null>(null);
  // A preference, not per-image state: it survives moving to the next image, because
  // re-choosing "boxes" on every frame of a folder is the opposite of a convenience.
  const [view, setView] = usePersistentState<AnnotationView>(
    'viewer.view',
    DEFAULT_VIEW,
    isAnnotationView,
  );
  // Mutually exclusive by construction rather than by a mode flag: choosing one clears
  // the other, so there is never a state where both claim to be the source.
  const [datasetId, setDatasetId] = usePersistentState<string | null>(
    'viewer.dataset',
    null,
    isNullable(isString),
  );
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  // A remembered dataset may have been deleted since: it is used only once the list
  // confirms it, so a stale id never reaches the image listing as a 404.
  const liveDataset = stillListed(datasetId ?? '', datasets.map((entry) => entry.id)) || null;
  const source = useImageSource(path, liveDataset);

  useEffect(() => {
    const controller = new AbortController();
    void listDatasets(controller.signal)
      .then(setDatasets)
      .catch(() => setDatasets([]));
    return () => controller.abort();
  }, []);

  const { current } = source;
  // The hook needs to know which image is on screen, or a result outlives the image it
  // describes — doc 21's stale-result bug.
  const run = useHeadRun(current?.path ?? null);

  const predictions = run.result?.predictions ?? [];
  const [minScore, setMinScore] = usePersistentState('viewer.minScore', DEFAULT_MIN_SCORE, isNumber);

  return (
    <section className="studio">
      <h2 className="studio__title">{t('run.viewer.title')}</h2>
      <p className="studio__lead">{t('run.viewer.lead')}</p>

      <fieldset className="modeswitch">
        <legend className="modeswitch__legend">{t('run.viewer.modeLegend')}</legend>
        {MODES.map((entry) => (
          <label
            key={entry.id}
            className={`modeswitch__option${mode === entry.id ? ' modeswitch__option--on' : ''}`}
          >
            <input
              type="radio"
              name="viewer-mode"
              value={entry.id}
              checked={mode === entry.id}
              onChange={() => setMode(entry.id)}
            />
            <span className="modeswitch__name">{t(entry.name)}</span>
            <span className="modeswitch__hint">{t(entry.hint)}</span>
          </label>
        ))}
      </fieldset>

      <ImageSourcePicker
        onPick={(picked) => {
          setDatasetId(null);
          setPath(picked);
        }}
        value={path ?? ''}
        busy={source.loading}
        datasets={datasets}
        datasetId={datasetId ?? ''}
        onPickDataset={(picked) => {
          setPath(null);
          setDatasetId(picked || null);
        }}
      />

      {/* Doc 68. Offered only when the source is a sequence — a single image probes as
          unplayable, and a play button that cannot play is worse than none. */}
      {mode === 'video' && (
        <SequencePanel
          path={path}
          view={view}
          foundationIds={run.selectedFoundations}
          instanceIds={run.selected}
          backboneId={run.backboneId ?? ''}
          concept={run.concept}
          onOpenAsImage={() => setMode('image')}
        />
      )}

      {source.error && (
        <p className="admin__error" role="alert">
          {source.error}
        </p>
      )}

      {source.empty && <p role="status">{t('run.viewer.emptyFolder')}</p>}

      {source.truncated && (
        <p role="status">{tp('run.viewer.truncated', source.items.length)}</p>
      )}

      {/* Outside the `current &&` guard on purpose (doc 34). Heads used to be pickable
          only after an image had loaded, which put the slowest decision — which of N
          heads to compare — behind a folder read. `useHeadRun` already lived at tab
          level, so the selection survived image changes; only the panel was gated.
          Running still needs an image, which is what `disabled` says. */}
      <HeadRunPanel
        state={run}
        onRun={() => current && void run.run(current.path)}
        disabled={source.loading}
        // Single-image runs draw only in the single-image view; in this mode they ran and
        // showed nothing (2026-10-02). The player analyses a sequence itself.
        runDisabled={!current || mode === 'video'}
        imageWidth={imageWidth}
      />

      {mode === 'image' && !current && !source.loading && (
        <p role="status" className="studio__hint">
          {tp('run.viewer.pickSource', run.selected.length)}
        </p>
      )}

      {/* One surface at a time. Showing the single-image panes under the player would run
          the same models twice over the same pixels and invite comparing the two. */}
      {mode === 'image' && current && (
        <>
          <p className="studio__path" title={current.path}>
            {t('run.viewer.position', {
              name: current.name,
              index: source.index + 1,
              total: source.items.length,
            })}
          </p>

          {/* Doc 67. One control for every pane rather than one each: comparing two
              segmenters means looking at them the same way, and per-pane views would make
              a difference in the control look like a difference in the models. */}
          <div className="studio__viewbar">
            <AnnotationViewToggle
              view={view}
              onChange={setView}
              hasMasks={predictions.some((entry) => entry.render_hint === 'masks')}
              hasBoxes={predictions.some(
                (entry) =>
                  entry.render_hint === 'masks' && Array.isArray(entry.payload['boxes']),
              )}
              disabled={run.running}
              groupName="viewer-view"
            />
            {predictions.some((entry) => entry.render_hint === 'boxes') && (
              <ScoreSlider value={minScore} onChange={setMinScore} />
            )}
          </div>

          {/* Hidden probe, the same one the Studio uses: the viewer's own image lives
              inside SideBySideViewer's render-prop and its natural size is not reachable
              from here. */}
          <img
            src={imageUrl(current.path)}
            alt=""
            hidden
            onLoad={(event) => setImageWidth(event.currentTarget.naturalWidth)}
          />

          {/* One pane per prediction. Comparing three segmenters is three panes; it is
              not a mode, and nothing here branches on how many there are. */}
          <SideBySideViewer
            imageUrl={imageUrl(current.path)}
            imageAlt={current.name}
            results={
              predictions.length > 0
                ? predictions.map((prediction) => ({
                    key: prediction.instance_id,
                    // Provenance, never a filename — doc 12's contract at the pane title.
                    label: prediction.head_name,
                    renderOverlay: (rendered) => (
                      <div className="overlay">
                        {renderOverlayFor(aboveScore(prediction, minScore), rendered, view)}
                      </div>
                    ),
                    note: <ScoreNote prediction={prediction} minScore={minScore} />,
                  }))
                : [
                    {
                      key: 'result',
                      label: t('run.compare.result'),
                      placeholder: (
                        <p className="viewer__placeholder">
                          {run.running ? t('run.viewer.running') : t('run.viewer.selectAndRun')}
                        </p>
                      ),
                    },
                  ]
            }
          />

          <div className="studio__actions">
            <button
              type="button"
              className="btn"
              disabled={!source.canGoPrevious}
              onClick={source.previous}
            >
              {t('run.viewer.previous')}
            </button>
            <button
              type="button"
              className="btn"
              disabled={!source.canGoNext}
              onClick={source.next}
            >
              {t('run.viewer.next')}
            </button>
          </div>
        </>
      )}
    </section>
  );
}

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
import { renderOverlayFor } from '../components/overlays/registry';
import { useHeadRun } from '../hooks/useHeadRun';
import { useImageSource } from '../hooks/useImageSource';

export function InferenceViewerTab(): JSX.Element {
  const [path, setPath] = useState<string | null>(null);
  // Read from the image itself rather than from any prediction: the tiling hint has to be
  // available *before* a run, which is exactly when there is no prediction to ask.
  const [imageWidth, setImageWidth] = useState<number | null>(null);
  // Mutually exclusive by construction rather than by a mode flag: choosing one clears
  // the other, so there is never a state where both claim to be the source.
  const [datasetId, setDatasetId] = useState<string | null>(null);
  const [datasets, setDatasets] = useState<readonly DatasetInfo[]>([]);
  const source = useImageSource(path, datasetId);

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

  return (
    <section className="studio">
      <h2 className="studio__title">Inference Viewer</h2>
      <p className="studio__lead">
        Point at a single image or a folder, pick one or more heads, and compare the
        original against what they predicted.
      </p>

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

      {source.error && (
        <p className="admin__error" role="alert">
          {source.error}
        </p>
      )}

      {source.empty && <p role="status">No images in that folder.</p>}

      {source.truncated && (
        <p role="status">Showing the first {source.items.length} images in that folder.</p>
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
        runDisabled={!current}
        imageWidth={imageWidth}
      />

      {!current && !source.loading && (
        <p role="status" className="studio__hint">
          Pick an image or a folder above to run the selected head{run.selected.length === 1 ? '' : 's'}.
        </p>
      )}

      {current && (
        <>
          <p className="studio__path" title={current.path}>
            {current.name} — {source.index + 1} of {source.items.length}
          </p>

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
                      <div className="overlay">{renderOverlayFor(prediction, rendered)}</div>
                    ),
                  }))
                : [
                    {
                      key: 'result',
                      label: 'Result',
                      placeholder: (
                        <p className="viewer__placeholder">
                          {run.running
                            ? 'Running…'
                            : 'Select one or more heads and press Run.'}
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
              ← Previous
            </button>
            <button
              type="button"
              className="btn"
              disabled={!source.canGoNext}
              onClick={source.next}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </section>
  );
}

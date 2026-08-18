/**
 * Wave 3 — Inference Viewer.
 *
 * Assembles the wave: an input source (doc 17), a head selection run through one shared
 * backbone pass (doc 18), the two panes (doc 19), and the overlays (doc 20).
 *
 * This file knows nothing about what a head produces. It hands predictions to
 * `renderOverlayFor`, which dispatches on `render_hint`.
 */

import { useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { HeadRunPanel } from '../components/HeadRunPanel';
import { ImageSourcePicker } from '../components/ImageSourcePicker';
import { SideBySideViewer } from '../components/SideBySideViewer';
import { renderOverlayFor } from '../components/overlays/registry';
import { useHeadRun } from '../hooks/useHeadRun';
import { useImageSource } from '../hooks/useImageSource';

export function InferenceViewerTab(): JSX.Element {
  const [path, setPath] = useState<string | null>(null);
  const source = useImageSource(path);
  const run = useHeadRun();
  const { current } = source;

  const predictions = run.result?.predictions ?? [];

  return (
    <section className="studio">
      <h2 className="studio__title">Inference Viewer</h2>
      <p className="studio__lead">
        Point at a single image or a folder, pick one or more heads, and compare the
        original against what they predicted.
      </p>

      <ImageSourcePicker onPick={setPath} value={path ?? ''} busy={source.loading} />

      {source.error && (
        <p className="admin__error" role="alert">
          {source.error}
        </p>
      )}

      {source.empty && <p role="status">No images in that folder.</p>}

      {source.truncated && (
        <p role="status">Showing the first {source.items.length} images in that folder.</p>
      )}

      {current && (
        <>
          <HeadRunPanel
            state={run}
            onRun={() => void run.run(current.path)}
            disabled={source.loading}
          />

          <p className="studio__path" title={current.path}>
            {current.name} — {source.index + 1} of {source.items.length}
          </p>

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

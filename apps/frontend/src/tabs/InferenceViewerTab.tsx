/**
 * Wave 3 — Inference Viewer.
 *
 * Feature 17 gives it an input source and nothing more: pick an image or a folder, step
 * through it, see which item is selected. Feature 19 replaces this layout with the
 * side-by-side panes and feature 20 draws the predictions; both consume `useImageSource`
 * exactly as it is used here.
 */

import { useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { ImageSourcePicker } from '../components/ImageSourcePicker';
import { useImageSource } from '../hooks/useImageSource';

export function InferenceViewerTab(): JSX.Element {
  const [path, setPath] = useState<string | null>(null);
  const source = useImageSource(path);
  const { current } = source;

  return (
    <section className="studio">
      <h2 className="studio__title">Inference Viewer</h2>
      <p className="studio__lead">
        Point at a single image or a folder of them. Heads and their overlays arrive with
        the rest of this wave.
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
          <p className="studio__path" title={current.path}>
            {current.name} — {source.index + 1} of {source.items.length}
          </p>

          <img className="viewer__image" src={imageUrl(current.path)} alt={current.name} />

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

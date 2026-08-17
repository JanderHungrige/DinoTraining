/** Wave 1 — Annotation Studio: the wave's demo-state, assembled. */

import { useRef, useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { AnnotationCanvas } from '../components/AnnotationCanvas';
import { CounterBar } from '../components/CounterBar';
import { SessionSetup } from '../components/SessionSetup';
import { useAnnotationSession, type SessionConfig } from '../hooks/useAnnotationSession';

export function AnnotationStudioTab(): JSX.Element {
  const [config, setConfig] = useState<SessionConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const session = useAnnotationSession(config);

  if (!config) {
    return (
      <section className="studio">
        <h2 className="studio__title">Annotation Studio</h2>
        <p className="studio__lead">
          Point at a folder of images, describe what you are looking for, and Grounding
          DINO proposes boxes for you to accept or reject.
        </p>
        <SessionSetup onStart={setConfig} />
      </section>
    );
  }

  const { currentImage, imageSize } = session;

  return (
    <section className="studio">
      <div className="studio__head">
        <h2 className="studio__title">Annotation Studio</h2>
        <button type="button" className="btn" onClick={() => setConfig(null)}>
          Change folder
        </button>
      </div>

      <CounterBar
        counts={session.counts}
        imageIndex={session.index}
        imageTotal={session.images.length}
        dirty={session.dirty}
      />

      {session.error && (
        <p className="admin__error" role="alert">
          {session.error}
        </p>
      )}

      {currentImage && (
        <>
          <p className="studio__path" title={currentImage}>
            {currentImage}
          </p>

          {/* Hidden probe: gives the session the natural size before any proposal,
              so boxes drawn by hand on a fresh image are still saveable. */}
          <img
            ref={imageRef}
            src={imageUrl(currentImage)}
            alt=""
            hidden
            onLoad={(event) =>
              session.reportImageSize(
                event.currentTarget.naturalWidth,
                event.currentTarget.naturalHeight,
              )
            }
          />

          {imageSize ? (
            <AnnotationCanvas
              imageUrl={imageUrl(currentImage)}
              naturalWidth={imageSize.width}
              naturalHeight={imageSize.height}
              boxes={session.boxes}
              selectedId={selectedId}
              onBoxesChange={session.setBoxes}
              onSelect={setSelectedId}
              disabled={session.busy}
            />
          ) : (
            <p role="status">Loading image…</p>
          )}

          <div className="studio__actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={session.proposing || session.busy}
              onClick={() => void session.propose()}
            >
              {session.proposing ? 'Detecting…' : 'Run prompt'}
            </button>
            <button
              type="button"
              className="btn"
              disabled={session.busy || !session.dirty}
              onClick={() => void session.save()}
            >
              {session.busy ? 'Saving…' : 'Save'}
            </button>
            <span className="studio__spacer" />
            <button
              type="button"
              className="btn"
              disabled={!session.canGoPrevious || session.busy}
              onClick={() => void session.previous()}
            >
              ← Previous
            </button>
            <button
              type="button"
              className="btn"
              disabled={!session.canGoNext || session.busy}
              onClick={() => void session.next()}
            >
              Next →
            </button>
          </div>
        </>
      )}
    </section>
  );
}

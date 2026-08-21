/** Wave 1 — Annotation Studio: the wave's demo-state, assembled. */

import { useCallback, useMemo, useRef, useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { AnnotationCanvas } from '../components/AnnotationCanvas';
import { CounterBar } from '../components/CounterBar';
import { BoxReviewList } from '../components/BoxReviewList';
import { PrescanPanel } from '../components/PrescanPanel';
import { SessionSetup } from '../components/SessionSetup';
import { hiddenByThreshold, numbered } from '../lib/boxReview';
import { usePrescan } from '../hooks/usePrescan';
import { prescanOptions, prescanSuggestions } from '../lib/prescanSource';
import type { Label } from '../types/annotation';
import { useAnnotationSession, type SessionConfig } from '../hooks/useAnnotationSession';

export function AnnotationStudioTab(): JSX.Element {
  const [config, setConfig] = useState<SessionConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Starts at 0 so nothing is ever hidden until the user asks. A review surface that opens
  // with boxes already filtered out looks like a model that found fewer than it did.
  const [threshold, setThreshold] = useState(0);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const session = useAnnotationSession(config);
  const prescan = usePrescan();

  const { boxes, setBoxes } = session;
  const items = useMemo(() => numbered(boxes), [boxes]);
  const hidden = useMemo(() => hiddenByThreshold(boxes, threshold), [boxes, threshold]);

  const setLabel = useCallback(
    (id: string, label: Label): void => {
      setBoxes(boxes.map((box) => (box.id === id ? { ...box, label } : box)));
    },
    [boxes, setBoxes],
  );

  const rename = useCallback(
    (id: string, text: string): void => {
      setBoxes(boxes.map((box) => (box.id === id ? { ...box, text } : box)));
    },
    [boxes, setBoxes],
  );

  const remove = useCallback(
    (id: string): void => {
      setBoxes(boxes.filter((box) => box.id !== id));
      setSelectedId((current) => (current === id ? null : current));
    },
    [boxes, setBoxes],
  );

  const startScan = useCallback(
    (labels: readonly string[], scoreThreshold: number): void => {
      if (config === null) return;
      void prescan.start(
        prescanOptions(config.source, session.allImages, labels, scoreThreshold),
      );
    },
    [config, prescan, session.allImages],
  );

  // Discards exactly what the slider is hiding, so what disappears is what was on screen.
  const removeHidden = useCallback((): void => {
    setBoxes(boxes.filter((box) => !hidden.has(box.id)));
  }, [boxes, hidden, setBoxes]);

  if (!config) {
    return (
      <section className="studio">
        <h2 className="studio__title">Annotation Studio</h2>
        <p className="studio__lead">
          Point at a folder of images and choose what proposes the boxes — describe what
          you are looking for, or run a head you already trained. Either way you accept,
          reject or correct what comes back.
        </p>
        <SessionSetup onStart={setConfig} />
      </section>
    );
  }

  const { currentImage, imageSize } = session;
  // The label names the mode, so the button is not the only thing on screen that knows
  // which one is running — the setup form's radios are behind "Change folder" by now.
  // A prompt is the only source you *write*; the other two you pick and run.
  const runLabel = config.source.kind === 'prompt' ? 'Run prompt' : 'Run model';

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
          <PrescanPanel
            total={session.allImages.length}
            job={prescan.job}
            starting={prescan.starting}
            running={prescan.running}
            error={prescan.error}
            filtered={session.filtered}
            suggestions={prescanSuggestions(config.source)}
            onScan={startScan}
            onCancel={prescan.cancel}
            onApply={(apply) =>
              session.setFilter(apply ? (prescan.job?.hits ?? []).map((h) => h.path) : null)
            }
          />

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
            <div className="studio__review">
              <AnnotationCanvas
                imageUrl={imageUrl(currentImage)}
                naturalWidth={imageSize.width}
                naturalHeight={imageSize.height}
                boxes={items}
                hidden={hidden}
                selectedId={selectedId}
                onBoxesChange={setBoxes}
                onSelect={setSelectedId}
                disabled={session.busy}
              />
              <BoxReviewList
                boxes={items}
                hidden={hidden}
                selectedId={selectedId}
                threshold={threshold}
                onSelect={setSelectedId}
                onLabel={setLabel}
                onRename={rename}
                onRemove={remove}
                onThreshold={setThreshold}
                onRemoveHidden={removeHidden}
                disabled={session.busy}
              />
            </div>
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
              {session.proposing ? 'Detecting…' : runLabel}
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

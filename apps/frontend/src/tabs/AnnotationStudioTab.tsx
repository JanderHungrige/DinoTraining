/** Wave 1 — Annotation Studio: the wave's demo-state, assembled. */

import { useCallback, useEffect, useMemo, useRef, useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { AnnotationCanvas } from '../components/AnnotationCanvas';
import { CounterBar } from '../components/CounterBar';
import { BoxReviewList } from '../components/BoxReviewList';
import { PrescanPanel } from '../components/PrescanPanel';
import { SessionSetup } from '../components/SessionSetup';
import { hiddenByThreshold, numbered } from '../lib/boxReview';
import { usePrescan } from '../hooks/usePrescan';
import { useBoxEditing } from '../hooks/useBoxEditing';
import { useDatasetClasses } from '../hooks/useDatasetClasses';
import { prescanOptions, prescanSuggestions } from '../lib/prescanSource';
import { useAnnotationSession, type SessionConfig } from '../hooks/useAnnotationSession';
import { AnnotationViewToggle } from '../components/AnnotationViewToggle';
import { DEFAULT_VIEW, type AnnotationView } from '../types/annotationView';

export function AnnotationStudioTab(): JSX.Element {
  const [config, setConfig] = useState<SessionConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // Starts at 0 so nothing is ever hidden until the user asks. A review surface that opens
  // with boxes already filtered out looks like a model that found fewer than it did.
  const [threshold, setThreshold] = useState(0);
  // Masks are the finer answer and the box is derivable from them, so the box is what you
  // opt into (doc 61). Not "hide the masks" — the two together are how you check that a
  // box is tight.
  // Doc 67 replaced a `showBoxes` boolean here. It could express "mask" and "mask + box"
  // but never "box alone", which is the view for checking extents against a detector.
  // A preference, not per-image state — it survives moving to the next image.
  const [view, setView] = useState<AnnotationView>(DEFAULT_VIEW);
  /**
   * Ids hidden by hand, so the image is clear enough to draw on.
   *
   * A **snapshot of what was there when it was pressed**, not a live predicate: a box
   * drawn afterwards is the whole point of pressing it, and a rule like "hide everything
   * not hand-drawn" would hide the new one the moment it was saved and reloaded. Null
   * means nothing is concealed.
   */
  const [concealed, setConcealed] = useState<ReadonlySet<string> | null>(null);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const session = useAnnotationSession(config);
  const prescan = usePrescan();

  const { boxes, setBoxes } = session;
  const items = useMemo(() => numbered(boxes), [boxes]);

  // Two reasons a box is not drawn, kept apart on purpose. `belowCutoff` is what the
  // slider is filtering and what `Remove N below` discards; `hidden` is everything not on
  // screen. Folding them together would make the remove button delete boxes the user only
  // asked to get out of the way — the worst thing this screen can do.
  const belowCutoff = useMemo(() => hiddenByThreshold(boxes, threshold), [boxes, threshold]);
  const hidden = useMemo(() => {
    if (concealed === null) return belowCutoff;
    const all = new Set(belowCutoff);
    for (const id of concealed) all.add(id);
    return all;
  }, [belowCutoff, concealed]);

  // Concealment is about the picture in front of you, so it does not survive moving to
  // the next one — and the ids would be stale anyway.
  useEffect(() => setConcealed(null), [session.currentImage]);

  // Classes on the canvas right now, offered alongside the stored vocabulary (doc 60).
  // A proposal run's classes are on screen and unsaved; a picker that could not offer
  // them would be visibly wrong about what this image contains.
  const inPlay = useMemo(
    () => boxes.map((box) => box.text ?? '').filter((text) => text !== ''),
    [boxes],
  );
  const vocabulary = useDatasetClasses(config?.datasetId ?? null, inPlay);

  // The toggle only exists when something on screen has a mask. A control that does
  // nothing reads as broken — the same rule doc 47 applied to the threshold slider.
  const anySegmented = useMemo(() => boxes.some((box) => box.mask !== undefined), [boxes]);

  const edit = useBoxEditing(boxes, setBoxes, (id) =>
    setSelectedId((current) => (current === id ? null : current)),
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

  /** Get everything currently on screen out of the way, or bring it all back. */
  const toggleConceal = useCallback((): void => {
    setConcealed((current) => (current === null ? new Set(boxes.map((box) => box.id)) : null));
  }, [boxes]);

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

      {session.loadingImages && <p role="status">Loading images…</p>}

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
                view={view}
                disabled={session.busy}
              />
              <BoxReviewList
                boxes={items}
                hidden={hidden}
                selectedId={selectedId}
                threshold={threshold}
                onSelect={setSelectedId}
                onLabel={edit.setLabel}
                onRename={edit.rename}
                onRemove={edit.remove}
                belowCutoff={belowCutoff}
                onThreshold={setThreshold}
                onRemoveHidden={() => edit.removeAll(belowCutoff)}
                classes={vocabulary.names}
                onCreateClass={vocabulary.create}
                onRenameClass={edit.renameClass}
                disabled={session.busy}
              />
            </div>
          ) : (
            <p role="status">Loading image…</p>
          )}

          <div className="studio__viewbar">
            <AnnotationViewToggle
              view={view}
              onChange={setView}
              hasMasks={anySegmented}
              hasBoxes={boxes.length > 0}
              disabled={session.busy}
              groupName="studio-view"
            />

            {/* Hiding what is already there is what makes drawing on a busy image
                possible: thirty proposals cover the thing you wanted to add. Nothing is
                deleted — hidden boxes are still saved, the same rule the slider follows. */}
            {(boxes.length > 0 || concealed !== null) && (
              <button type="button" className="btn btn--small" onClick={toggleConceal}>
                {concealed === null
                  ? `Hide the ${boxes.length} box${boxes.length === 1 ? '' : 'es'} already here`
                  : `Show ${concealed.size} hidden box${concealed.size === 1 ? '' : 'es'}`}
              </button>
            )}
          </div>

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

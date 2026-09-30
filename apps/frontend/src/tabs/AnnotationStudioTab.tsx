/** Wave 1 — Annotation Studio: the wave's demo-state, assembled. */

import { useCallback, useEffect, useMemo, useRef, useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { AnnotationCanvas } from '../components/AnnotationCanvas';
import { CounterBar } from '../components/CounterBar';
import { BoxReviewList } from '../components/BoxReviewList';
import { PrescanPanel } from '../components/PrescanPanel';
import { SessionSetup } from '../components/SessionSetup';
import { TargetGuide } from '../components/TargetGuide';
import { PhraseBar } from '../components/phrases/PhraseBar';
import { GuidelinePanel } from '../components/GuidelinePanel';
import { SecondLook } from '../components/SecondLook';
import { useSecondLook } from '../hooks/useSecondLook';
import { useAnnotationTargetList } from '../hooks/useAnnotationTargetList';
import { usePicturePhrases } from '../hooks/usePicturePhrases';
import { hiddenByThreshold, numbered } from '../lib/boxReview';
import { usePrescan } from '../hooks/usePrescan';
import { useBoxEditing } from '../hooks/useBoxEditing';
import { useDatasetClasses } from '../hooks/useDatasetClasses';
import { prescanOptions, prescanSuggestions } from '../lib/prescanSource';
import { useAnnotationSession, type SessionConfig } from '../hooks/useAnnotationSession';
import { MaskEditBar } from '../components/MaskEditBar';
import { MaskEditOverlay } from '../components/MaskEditOverlay';
import { StudioActions } from '../components/StudioActions';
import { StudioBack } from '../components/StudioBack';
import { StudioViewBar } from '../components/StudioViewBar';
import { useMaskEditing } from '../hooks/useMaskEditing';
import { useT } from '../i18n';
import { DEFAULT_VIEW, type AnnotationView } from '../types/annotationView';

export interface AnnotationStudioTabProps {
  /** False while another tab is shown: App keeps the Studio mounted so the session
   *  survives, and its document-wide keys must not act on a hidden picture. */
  readonly active?: boolean;
}

export function AnnotationStudioTab({ active = true }: AnnotationStudioTabProps): JSX.Element {
  const { t } = useT();
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
  // Doc 104: what this dataset is annotated for, and what this picture still lacks.
  const target = useAnnotationTargetList().find((entry) => entry.id === (config?.target ?? 'open'));
  const pictures = usePicturePhrases(config?.datasetId ?? null, session.currentImage);
  const maskEditing = useMaskEditing(session.currentImage, session.boxes, session.setBoxes, selectedId);
  const selectedBox = session.boxes.find((box) => box.id === selectedId) ?? null;
  // Doc 109: a second look reuses the prescan's picture filter.
  const look = useSecondLook(config?.datasetId ?? '', session.setFilter);

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
  // A phrase with a class of its own is a class too, before any outline carries it (Jan,
  // 2026-09-30: "+ phrase" added "flame reflection", and the list's picker did not offer it).
  const inPlay = useMemo(
    () => [
      ...boxes.map((box) => box.text ?? '').filter((text) => text !== ''),
      ...pictures.phrases.map((phrase) => phrase.class_name),
    ],
    [boxes, pictures.phrases],
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
        <p className="studio__lead">{t('studio.tab.lead')}</p>
        <SessionSetup onStart={setConfig} />
      </section>
    );
  }

  const { currentImage, imageSize } = session;
  // The label names the mode, so the button is not the only thing on screen that knows
  // which one is running — the setup form's radios are behind "Change folder" by now.
  // A prompt is the only source you *write*; the other two you pick and run.
  const runLabel = t(config.source.kind === 'prompt' ? 'studio.tab.runPrompt' : 'studio.tab.runModel');

  return (
    <section className="studio">
      <div className="studio__head">
        <h2 className="studio__title">Annotation Studio</h2>
        <StudioBack dirty={session.dirty} busy={session.busy} onSave={session.save} onBack={() => setConfig(null)} />
      </div>

      <CounterBar
        counts={session.counts}
        imageIndex={session.index}
        imageTotal={session.images.length}
        dirty={session.dirty}
      />

      {target && (
        <TargetGuide
          target={target}
          boxes={boxes}
          phraseCount={pictures.phrases.length}
          statuses={pictures.statuses}
        />
      )}

      <GuidelinePanel datasetId={config.datasetId} />
      <SecondLook look={look} currentImage={session.currentImage} disabled={session.busy} />

      {session.error && (
        <p className="admin__error" role="alert">
          {session.error}
        </p>
      )}

      {session.loadingImages && <p role="status">{t('studio.tab.loadingImages')}</p>}

      {currentImage && (
        <>
          <PrescanPanel
            storageKey="studio.prescan"
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

          {/* Hidden probe: the natural size before any proposal, so hand-drawn boxes save. */}
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

          <PhraseBar
            datasetId={config.datasetId}
            pictures={pictures}
            open={['sam3', 'open', undefined].includes(config.target)}
            disabled={session.busy || !active}
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
                overlay={(rendered) => (
                  <MaskEditOverlay
                    rendered={rendered}
                    tool={maskEditing.tool}
                    radius={maskEditing.radius}
                    points={maskEditing.points}
                    onClick={maskEditing.click}
                    onStroke={maskEditing.stroke}
                  />
                )}
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
            <p role="status">{t('studio.tab.loadingImage')}</p>
          )}

          <StudioViewBar
            view={view}
            onView={setView}
            hasMasks={anySegmented}
            boxCount={boxes.length}
            concealed={concealed?.size ?? null}
            onToggleConceal={toggleConceal}
            disabled={session.busy}
          />

          <MaskEditBar
            editing={maskEditing}
            selection={selectedBox === null ? 'none' : selectedBox.mask ? 'outline' : 'box'}
            disabled={session.busy}
          />

          <StudioActions session={session} runLabel={runLabel} />
        </>
      )}
    </section>
  );
}

/** Wave 4 — Dataset Generator: a trained head proposes, the user reviews. */

import { useCallback, useRef, useState, type JSX } from 'react';

import { imageUrl } from '../api/annotate';
import { AnnotationCanvas } from '../components/AnnotationCanvas';
import { numbered } from '../lib/boxReview';
import { CounterBar } from '../components/CounterBar';
import { PrescanPanel } from '../components/PrescanPanel';
import { usePrescan } from '../hooks/usePrescan';
import {
  generatorPrescanOptions,
  generatorPrescanSuggestions,
} from '../lib/prescanSource';
import { MaskReviewCanvas } from '../components/MaskReviewCanvas';
import { AnnotationViewToggle } from '../components/AnnotationViewToggle';
import { DEFAULT_VIEW, type AnnotationView } from '../types/annotationView';
import { GeneratorSetup } from '../components/GeneratorSetup';
import { usePersistentState } from '../hooks/usePersistentState';
import { isAnnotationView, isBoolean } from '../lib/persisted';
import { useAutoPropose } from '../hooks/useAutoPropose';
import { useAutoplay } from '../hooks/useAutoplay';
import { AutoplayControls } from '../components/AutoplayControls';
import { AutoplayBar, AutoplaySummary } from '../components/AutoplayProgress';
import { GeneratorActionBar } from '../components/GeneratorActionBar';
import {
  useGeneratorSession,
  type GeneratorConfig,
} from '../hooks/useGeneratorSession';

export function DatasetGeneratorTab(): JSX.Element {
  const [config, setConfig] = useState<GeneratorConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // A preference across the whole folder, not per-image state.
  const [view, setView] = usePersistentState<AnnotationView>(
    'generator.view',
    DEFAULT_VIEW,
    isAnnotationView,
  );
  const imageRef = useRef<HTMLImageElement | null>(null);
  const session = useGeneratorSession(config);
  // Doc 70: both on by default, and remembered.
  const [autoPropose, setAutoPropose] = usePersistentState('generator.autoPropose', true, isBoolean);
  const [autoSave, setAutoSave] = usePersistentState('generator.autoSave', true, isBoolean);
  const autoplay = useAutoplay(config, session);
  // Autoplay proposes for itself; a second proposer racing it would be a second opinion.
  useAutoPropose(session, config !== null && autoPropose && !autoplay.running);
  const locked = autoplay.running;
  const prescan = usePrescan();

  const startScan = useCallback(
    (labels: readonly string[], scoreThreshold: number): void => {
      if (config === null) return;
      void prescan.start(
        generatorPrescanOptions(config, session.allImages, labels, scoreThreshold),
      );
    },
    [config, prescan, session.allImages],
  );

  if (!config) {
    return (
      <section className="studio">
        <h2 className="studio__title">Dataset Generator</h2>
        <p className="studio__lead">
          Point a head you have already trained at new images. It proposes boxes, you accept
          or reject them, and the result becomes the dataset for the next head.
        </p>
        <GeneratorSetup onStart={setConfig} />
      </section>
    );
  }

  const { currentImage, imageSize } = session;

  return (
    <section className="studio">
      <div className="studio__head">
        <h2 className="studio__title">Dataset Generator</h2>
        <button type="button" className="btn" onClick={() => setConfig(null)}>
          Change setup
        </button>
      </div>

      <CounterBar
        counts={session.counts}
        imageIndex={session.index}
        imageTotal={session.images.length}
        dirty={session.dirty}
      />

      {session.producerName && (
        <p className="studio__lead">
          Proposing with <strong>{session.producerName}</strong>
          {session.producerDetail ? ` — ${session.producerDetail}` : ''}
        </p>
      )}

      {session.error && (
        <p className="admin__error" role="alert">
          {session.error}
        </p>
      )}

      {session.loading && <p role="status">Listing images…</p>}

      {/* Unattended runs benefit at least as much as the Studio: the Generator proposes on
          every image whether or not there is anything in it, and reviewing 400 crops of
          ballast is the same wasted afternoon. */}
      {!session.loading && session.allImages.length > 0 && (
        <PrescanPanel
          storageKey="generator.prescan"
          total={session.allImages.length}
          job={prescan.job}
          starting={prescan.starting}
          running={prescan.running}
          error={prescan.error}
          filtered={session.filtered}
          suggestions={generatorPrescanSuggestions(config)}
          onScan={startScan}
          onCancel={prescan.cancel}
          onApply={(apply) =>
            session.setFilter(apply ? (prescan.job?.hits ?? []).map((h) => h.path) : null)
          }
        />
      )}

      {!session.loading && session.images.length === 0 && (
        <p role="status">No images in that folder.</p>
      )}

      {currentImage && (
        <>
          <p className="studio__path" title={currentImage}>
            {session.index + 1} / {session.images.length} · {currentImage}
          </p>

          {/* Hidden probe: gives the natural size before any proposal, so the canvas can
              render — and boxes drawn by hand are placed correctly — on an image the head
              has not been run over yet. */}
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

          {/* Which review surface is a property of the config, not of what happens to
              be in state: an empty mask list must still show the mask canvas, or "found
              nothing" would silently render the box canvas instead. */}
          {locked && autoplay.hidden ? (
            <AutoplayBar progress={autoplay.progress} />
          ) : imageSize ? (
            config.kind === 'masks' ? (
              <MaskReviewCanvas
                imageUrl={imageUrl(currentImage)}
                naturalWidth={imageSize.width}
                naturalHeight={imageSize.height}
                masks={session.masks}
                selectedId={selectedId}
                onMasksChange={session.setMasks}
                onSelect={setSelectedId}
                view={view}
                disabled={session.proposing || locked}
              />
            ) : (
              <AnnotationCanvas
                imageUrl={imageUrl(currentImage)}
                naturalWidth={imageSize.width}
                naturalHeight={imageSize.height}
                boxes={numbered(session.boxes)}
                selectedId={selectedId}
                onBoxesChange={session.setBoxes}
                onSelect={setSelectedId}
                disabled={session.proposing || locked}
              />
            )
          ) : (
            <p role="status">Loading image…</p>
          )}

          {/* Doc 67. Only a mask run has two halves to choose between; a box run gets no
              control, because `AnnotationViewToggle` renders nothing for one option. */}
          <div className="studio__viewbar">
            <AnnotationViewToggle
              view={view}
              onChange={setView}
              hasMasks={config.kind === 'masks'}
              hasBoxes={config.kind === 'masks' && session.masks.length > 0}
              disabled={session.proposing}
              groupName="generator-view"
            />
          </div>

          <GeneratorActionBar
            proposeLabel={config.kind === 'masks' ? 'Propose masks' : 'Propose boxes'}
            proposing={session.proposing}
            saving={session.saving}
            dirty={session.dirty}
            canGoPrevious={session.canGoPrevious}
            canGoNext={session.canGoNext}
            autoPropose={autoPropose}
            autoSave={autoSave}
            onAutoProposeChange={setAutoPropose}
            onAutoSaveChange={setAutoSave}
            onPropose={() => void session.propose()}
            onSave={() => void session.save()}
            onPrevious={() => void session.previous({ autoSave })}
            onNext={() => void session.next({ autoSave })}
            locked={locked}
          >
            <AutoplayControls
              autoplay={autoplay}
              canPlay={!session.proposing && !session.saving && session.images.length > 0}
            />
          </GeneratorActionBar>

          {!locked && autoplay.report && <AutoplaySummary report={autoplay.report} />}

        </>
      )}
    </section>
  );
}

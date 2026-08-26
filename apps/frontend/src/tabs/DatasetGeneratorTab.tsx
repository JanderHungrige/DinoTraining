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
import {
  useGeneratorSession,
  type GeneratorConfig,
} from '../hooks/useGeneratorSession';

export function DatasetGeneratorTab(): JSX.Element {
  const [config, setConfig] = useState<GeneratorConfig | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  // A preference across the whole folder, not per-image state.
  const [view, setView] = useState<AnnotationView>(DEFAULT_VIEW);
  const imageRef = useRef<HTMLImageElement | null>(null);
  const session = useGeneratorSession(config);
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
          {imageSize ? (
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
                disabled={session.proposing}
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
                disabled={session.proposing}
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

          <div className="studio__actions">
            <button
              type="button"
              className="btn btn--primary"
              disabled={session.proposing}
              onClick={() => void session.propose()}
            >
              {session.proposing
                ? 'Proposing…'
                : config.kind === 'masks'
                  ? 'Propose masks'
                  : 'Propose boxes'}
            </button>
            <button
              type="button"
              className="btn"
              disabled={session.saving || session.proposing || !session.dirty}
              onClick={() => void session.save()}
            >
              {session.saving ? 'Saving…' : 'Save to dataset'}
            </button>
            <span className="studio__spacer" />
            <button
              type="button"
              className="btn"
              disabled={!session.canGoPrevious || session.proposing}
              onClick={session.previous}
            >
              ← Previous
            </button>
            <button
              type="button"
              className="btn"
              disabled={!session.canGoNext || session.proposing}
              onClick={session.next}
            >
              Next →
            </button>
          </div>

        </>
      )}
    </section>
  );
}

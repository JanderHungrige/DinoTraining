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
import { isAnnotationView, isBoolean, isShapeOf } from '../lib/persisted';
import { useAutoPropose } from '../hooks/useAutoPropose';
import { useAutoplay } from '../hooks/useAutoplay';
import { AutoplayControls, AutoplayHiddenOption } from '../components/AutoplayControls';
import { AutoplayBar, AutoplaySummary } from '../components/AutoplayProgress';
import { UnclearBandField } from '../components/UnclearBandField';
import { UnclearQuestion } from '../components/UnclearQuestion';
import { DEFAULT_BAND, normaliseBand } from '../lib/unclearBand';
import { GeneratorActionBar } from '../components/GeneratorActionBar';
import { useT } from '../i18n';
import {
  useGeneratorSession,
  type GeneratorConfig,
} from '../hooks/useGeneratorSession';

const isBand = isShapeOf(DEFAULT_BAND);

export interface DatasetGeneratorTabProps {
  /** Doc 74: jump to Inspect at this run's dataset, and at its video or folder. */
  readonly onInspect?: (datasetId: string, sequence: string | null) => void;
}

/** The sequence a run's frames were recorded under (doc 73), for Inspect to open at. */
function sequenceOf(config: GeneratorConfig): string | null {
  if (config.images.kind === 'video') return config.images.path;
  if (config.images.kind === 'folder') return config.images.folder;
  return null;
}

export function DatasetGeneratorTab({ onInspect }: DatasetGeneratorTabProps = {}): JSX.Element {
  const { t } = useT();
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
  // Doc 72: off by default; the band is the user's, because every model scores differently.
  const [askUnclear, setAskUnclear] = usePersistentState('generator.askUnclear', false, isBoolean);
  const [band, setBand] = usePersistentState('generator.unclearBand', DEFAULT_BAND, isBand);
  const autoplay = useAutoplay(config, session, askUnclear ? normaliseBand(band) : null);
  // Autoplay proposes for itself; a second proposer racing it would be a second opinion.
  useAutoPropose(session, config !== null && autoPropose && !autoplay.running);
  // While autoplay waits on a question, the canvas is the user's again; nothing else is.
  const locked = autoplay.running && autoplay.question === null;
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
        <h2 className="studio__title">{t('generator.tab.title')}</h2>
        <p className="studio__lead">{t('generator.tab.lead')}</p>
        <GeneratorSetup onStart={setConfig} />
      </section>
    );
  }

  const { currentImage, imageSize } = session;

  return (
    <section className="studio">
      <div className="studio__head">
        <h2 className="studio__title">{t('generator.tab.title')}</h2>
        <span className="studio__headactions">
          {onInspect && (
            <button
              type="button"
              className="btn"
              disabled={autoplay.running}
              onClick={() => onInspect(config.datasetId, sequenceOf(config))}
            >
              {t('generator.tab.inspect')}
            </button>
          )}
          <button type="button" className="btn" onClick={() => setConfig(null)}>
            {t('generator.tab.changeSetup')}
          </button>
        </span>
      </div>

      <CounterBar
        counts={session.counts}
        imageIndex={session.index}
        imageTotal={session.images.length}
        dirty={session.dirty}
      />

      {session.producerName && (
        <p className="studio__lead">
          {t('generator.tab.proposingWith')} <strong>{session.producerName}</strong>
          {session.producerDetail ? ` — ${session.producerDetail}` : ''}
        </p>
      )}

      {session.error && (
        <p className="admin__error" role="alert">
          {session.error}
        </p>
      )}

      {session.loading &&
        (session.decoding ? (
          // Doc 73: a video is decoded into the dataset before the first image can show.
          <p role="status">
            {t('generator.tab.decoding', {
              done: session.decoding.done,
              total: session.decoding.total,
            })}{' '}
            <progress max={Math.max(1, session.decoding.total)} value={session.decoding.done} />
          </p>
        ) : (
          <p role="status">{t('generator.tab.listing')}</p>
        ))}

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
        <p role="status">{t('generator.tab.noImages')}</p>
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
            <p role="status">{t('generator.tab.loadingImage')}</p>
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
            proposeLabel={t(config.kind === 'masks' ? 'generator.tab.proposeMasks' : 'generator.tab.proposeBoxes')}
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
            locked={autoplay.running}
            options={<AutoplayHiddenOption autoplay={autoplay} />}
          >
            <AutoplayControls
              autoplay={autoplay}
              canPlay={!session.proposing && !session.saving && session.images.length > 0}
            />
          </GeneratorActionBar>

          {autoplay.question && (
            <UnclearQuestion
              imageNumber={autoplay.question.index + 1}
              imageTotal={session.images.length}
              count={autoplay.question.count}
              band={normaliseBand(band)}
              onContinue={autoplay.answer}
              onStop={autoplay.stop}
            />
          )}

          <UnclearBandField
            enabled={askUnclear}
            band={band}
            disabled={autoplay.running}
            onEnabledChange={setAskUnclear}
            onBandChange={setBand}
          />

          {!autoplay.running && autoplay.report && <AutoplaySummary report={autoplay.report} />}

        </>
      )}
    </section>
  );
}

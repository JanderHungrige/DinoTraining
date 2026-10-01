/**
 * The first-run setup screen (doc 127): what this machine is, what gets installed, the
 * install with its progress, and Dino Run to pass the time.
 */

import { useCallback, useEffect, useRef, useState, type JSX } from 'react';

import { LanguageSwitch } from '../components/LanguageSwitch';
import { useT } from '../i18n';
import { DinoRun } from './DinoRun';
import { SetupFailureNotice } from './SetupFailureNotice';
import { MachineSummary, variantLabel } from './MachineSummary';
import { onProgress, percent, report, setupInstall, startPrevious, CUDA_VERSION, type Machine, type Progress, type SetupFailure, type Variant } from './shell';
import { SetupTips } from './SetupTips';
import './setup.css';

type Stage =
  | { readonly kind: 'choose' }
  /** Downloading, installing, then starting the backend: one call to the shell. */
  | { readonly kind: 'installing'; readonly variant: Variant }
  /** Doc 129: starting on the previous packages after a failed update. */
  | { readonly kind: 'resuming' }
  | { readonly kind: 'ready' }
  | { readonly kind: 'failed'; readonly variant: Variant; readonly failure: SetupFailure };

interface SetupScreenProps {
  readonly machine: Machine;
  /** Install this variant straight away (`DINO_SETUP_AUTO`, an unattended install). */
  readonly auto?: Variant | null;
  readonly onDone: () => void;
  /**
   * Doc 128: the Admin tab's switch runs this screen with another shell command, and a
   * failed switch can go back to the (rolled-back, working) app.
   */
  readonly switching?: { readonly run: (variant: Variant) => Promise<void>; readonly onBack: () => void };
  /** Doc 129: an environment from an older lock is being updated; its variant. */
  readonly update?: Variant | null;
}

export function SetupScreen({ machine, auto = null, onDone, switching, update = null }: SetupScreenProps): JSX.Element {
  const { t } = useT();
  const [stage, setStage] = useState<Stage>({ kind: 'choose' });
  const [progress, setProgress] = useState<Progress | null>(null);
  const [played, setPlayed] = useState(false);

  useEffect(() => report(stage.kind === 'choose' ? 'shown' : stage.kind), [stage.kind]);
  useEffect(() => {
    if (progress?.phase === 'done') report('starting');
  }, [progress?.phase]);
  const open = useCallback(() => {
    report('opened');
    onDone();
  }, [onDone]);

  useEffect(() => {
    let stop: (() => void) | null = null;
    let cancelled = false;
    void onProgress(setProgress).then((unlisten) => (cancelled ? unlisten() : (stop = unlisten)));
    return () => {
      cancelled = true;
      stop?.();
    };
  }, []);

  // Nobody played: open the app as soon as it is ready. Someone is playing: let them.
  useEffect(() => {
    if (stage.kind === 'ready' && !played) open();
  }, [stage, played, open]);

  const install = useCallback(
    async (variant: Variant) => {
      setProgress(null);
      setStage({ kind: 'installing', variant });
      try {
        await (switching ? switching.run(variant) : setupInstall(variant));
      } catch (failure) {
        setStage({ kind: 'failed', variant, failure: failure as SetupFailure });
        return;
      }
      // The shell returns once the backend answers `/health`.
      setStage({ kind: 'ready' });
    },
    [switching],
  );

  const started = useRef(false);
  useEffect(() => {
    if (auto && !started.current) {
      started.current = true;
      void install(auto);
    }
  }, [auto, install]);

  const resume = useCallback(async () => {
    setStage({ kind: 'resuming' });
    try {
      await startPrevious();
      setStage({ kind: 'ready' });
    } catch (failure) {
      setStage({ kind: 'failed', variant: update ?? 'cpu', failure: failure as SetupFailure });
    }
  }, [update]);
  const secondary = switching
    ? { label: t('setup.back'), onClick: switching.onBack }
    : update
      ? { label: t('setup.update.previous'), onClick: () => void resume() }
      : undefined;
  const title = switching && auto
    ? t(CUDA_VERSION[auto] ? 'setup.switch.titleGpu' : 'setup.switch.titleCpu')
    : t(update ? 'setup.update.title' : 'setup.title');
  const intro = t(switching ? 'setup.switch.intro' : update ? 'setup.update.intro' : 'setup.intro');

  const busy = stage.kind === 'installing' || stage.kind === 'resuming' || stage.kind === 'ready';
  return (
    <div className="firstrun">
      <header className="firstrun__header">
        <h1 className="firstrun__title">{title}</h1>
        <LanguageSwitch />
      </header>
      <section className="firstrun__card" aria-live="polite">
        <p className="firstrun__intro">{intro}</p>
        <MachineSummary machine={machine} />
        {stage.kind === 'choose' && <Choices machine={machine} onInstall={(v) => void install(v)} />}
        {stage.kind === 'failed' && (
          <SetupFailureNotice
            failure={stage.failure}
            onRetry={() => void install(stage.variant)}
            {...(secondary ? { secondary } : {})}
          />
        )}
        {busy && <InstallProgress stage={stage} progress={progress} onOpen={open} />}
      </section>
      {busy && (
        <section className="firstrun__wait">
          <DinoRun onPlay={() => setPlayed(true)} />
          <SetupTips />
        </section>
      )}
    </div>
  );
}

function Choices({ machine, onInstall }: { readonly machine: Machine; readonly onInstall: (v: Variant) => void }): JSX.Element | null {
  const { t, lang } = useT();
  const [first, ...others] = machine.choices;
  if (!first) return null;
  return (
    <div className="firstrun__choices">
      <button type="button" className="btn btn--primary" onClick={() => onInstall(first.variant)}>
        {variantLabel(t, lang, first, machine)}
      </button>
      {others.map((choice) => (
        <button key={choice.variant} type="button" className="btn" onClick={() => onInstall(choice.variant)}>
          {variantLabel(t, lang, choice, machine)}
        </button>
      ))}
    </div>
  );
}

interface InstallProgressProps {
  readonly stage: Stage;
  readonly progress: Progress | null;
  readonly onOpen: () => void;
}

function InstallProgress({ stage, progress, onOpen }: InstallProgressProps): JSX.Element {
  const { t } = useT();
  const value = stage.kind === 'installing' ? percent(progress) : 100;
  const phase = progress?.phase ?? 'python';
  const label =
    stage.kind === 'ready'
      ? t('setup.progress.ready')
      : phase === 'done' || stage.kind === 'resuming'
        ? t('setup.progress.starting')
        : t(`setup.progress.${phase}`, {
            done: String(Math.round(progress?.done_mb ?? 0)),
            total: String(Math.round(progress?.total_mb ?? 0)),
          });
  return (
    <div className="firstrun__progress">
      <div className="firstrun__bar" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={value} aria-label={label}>
        <div className="firstrun__fill" style={{ width: `${value}%` }} />
      </div>
      <p className="firstrun__status">
        <span>{label}</span>
        <span className="firstrun__percent">{value} %</span>
      </p>
      {stage.kind === 'installing' && progress?.current && (
        <p className="firstrun__current">{t('setup.progress.current', { name: progress.current })}</p>
      )}
      {stage.kind === 'ready' && (
        <button type="button" className="btn btn--primary" onClick={onOpen}>
          {t('setup.open')}
        </button>
      )}
    </div>
  );
}

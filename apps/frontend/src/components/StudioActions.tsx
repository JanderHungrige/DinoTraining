/**
 * Run, Save, Previous, Next — the Studio's action row, the Generator's bar (doc 70): the
 * four buttons side by side, and Auto-propose / Auto-save named in full below them
 * (Jan, 2026-09-30). Split out of the Studio at the 300-line gate.
 *
 * Auto-save on is what the Studio always did: moving on saves first. Off, moving on with
 * unsaved changes is refused with a note rather than dropping them — the Generator's
 * "move on anyway" would lose ten minutes of outlining to one click.
 */

import { useEffect, useRef, useState, type JSX } from 'react';

import type { AnnotationSession } from '../hooks/useAnnotationSession';
import { usePersistentState } from '../hooks/usePersistentState';
import { useT } from '../i18n';
import { isBoolean } from '../lib/persisted';
import { GeneratorActionBar } from './GeneratorActionBar';

/** Propose once per picture that arrives with nothing on it. In a review for one class
 *  (doc 119) also over existing annotations: the result is added, never replacing them. */
function useStudioAutoPropose(session: AnnotationSession, enabled: boolean, only?: string): void {
  const askedFor = useRef<string | null>(null);
  const { currentImage, proposing, busy, boxes, propose } = session;
  useEffect(() => {
    if (!enabled || currentImage === null || proposing || busy) return;
    if (askedFor.current === currentImage || (boxes.length > 0 && only === undefined)) return;
    askedFor.current = currentImage;
    void propose(only);
  }, [enabled, currentImage, proposing, busy, boxes.length, propose, only]);
}

export interface StudioActionsProps {
  readonly session: AnnotationSession;
  readonly runLabel: string;
  /** Doc 119: the class under review — proposals for it alone, added. */
  readonly only?: string;
}

export function StudioActions({ session, runLabel, only }: StudioActionsProps): JSX.Element {
  const { t } = useT();
  const [autoPropose, setAutoPropose] = usePersistentState('studio.autoPropose', false, isBoolean);
  const [autoSave, setAutoSave] = usePersistentState('studio.autoSave', true, isBoolean);
  const [blocked, setBlocked] = useState(false);
  useStudioAutoPropose(session, autoPropose, only);
  useEffect(() => setBlocked(false), [session.dirty, autoSave]);

  const move = (go: () => Promise<void>): void => {
    if (!autoSave && session.dirty) {
      setBlocked(true);
      return;
    }
    void go();
  };

  return (
    <>
      <GeneratorActionBar
        proposeLabel={runLabel}
        proposing={session.proposing}
        saving={session.busy}
        dirty={session.dirty}
        canGoPrevious={session.canGoPrevious}
        canGoNext={session.canGoNext}
        autoPropose={autoPropose}
        autoSave={autoSave}
        onAutoProposeChange={setAutoPropose}
        onAutoSaveChange={setAutoSave}
        onPropose={() => void session.propose(only)}
        onSave={() => void session.save()}
        onPrevious={() => move(session.previous)}
        onNext={() => move(session.next)}
      />
      {blocked && (
        <p className="run__warn" role="alert">
          {t('studio.actions.unsavedBlocked')}
        </p>
      )}
    </>
  );
}

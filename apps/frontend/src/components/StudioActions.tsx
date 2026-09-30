/**
 * Run, Save, Previous, Next — the Studio's action row. Split out of the Studio (at the
 * 300-line gate) when doc 106 added the outline tools.
 */

import type { JSX } from 'react';

import type { AnnotationSession } from '../hooks/useAnnotationSession';
import { useT } from '../i18n';

export function StudioActions({ session, runLabel }: { readonly session: AnnotationSession; readonly runLabel: string }): JSX.Element {
  const { t } = useT();
  return (
    <div className="studio__actions">
      <button
        type="button"
        className="btn btn--primary"
        disabled={session.proposing || session.busy}
        onClick={() => void session.propose()}
      >
        {session.proposing ? t('studio.actions.detecting') : runLabel}
      </button>
      <button
        type="button"
        className="btn"
        disabled={session.busy || !session.dirty}
        onClick={() => void session.save()}
      >
        {session.busy ? t('studio.actions.saving') : t('common.save')}
      </button>
      <span className="studio__spacer" />
      <button
        type="button"
        className="btn"
        disabled={!session.canGoPrevious || session.busy}
        onClick={() => void session.previous()}
      >
        {t('studio.actions.previous')}
      </button>
      <button
        type="button"
        className="btn"
        disabled={!session.canGoNext || session.busy}
        onClick={() => void session.next()}
      >
        {t('studio.actions.next')}
      </button>
    </div>
  );
}

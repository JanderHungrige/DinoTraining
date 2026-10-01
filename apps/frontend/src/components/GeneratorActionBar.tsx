/**
 * The Generator's toolbar (doc 70): Propose and Save sit directly beside Previous and Next,
 * each with an "auto" box, so reviewing a folder is one click per image instead of four
 * spread across the width of the screen.
 *
 * The automation boxes sit in a row of their own below the buttons, each named in full
 * ("Auto-propose", "Auto-save"). A bare "auto" next to a button left people guessing which
 * button it belonged to once the toolbar wrapped (Jan, 2026-09-30).
 */

import type { JSX, ReactNode } from 'react';

import { useT } from '../i18n';

export interface GeneratorActionBarProps {
  readonly proposeLabel: string;
  readonly proposing: boolean;
  readonly saving: boolean;
  readonly dirty: boolean;
  readonly canGoPrevious: boolean;
  readonly canGoNext: boolean;
  readonly autoPropose: boolean;
  readonly autoSave: boolean;
  /** Everything is locked while autoplay drives the session (doc 71). */
  readonly locked?: boolean;
  readonly onAutoProposeChange: (value: boolean) => void;
  readonly onAutoSaveChange: (value: boolean) => void;
  readonly onPropose: () => void;
  readonly onSave: () => void;
  readonly onPrevious: () => void;
  readonly onNext: () => void;
  /** Room for the autoplay button, kept in the same cluster. */
  readonly children?: ReactNode;
  /** More option boxes for the row below, e.g. autoplay's "Run hidden". */
  readonly options?: ReactNode;
}

export function GeneratorActionBar({
  proposeLabel,
  proposing,
  saving,
  dirty,
  canGoPrevious,
  canGoNext,
  autoPropose,
  autoSave,
  locked = false,
  onAutoProposeChange,
  onAutoSaveChange,
  onPropose,
  onSave,
  onPrevious,
  onNext,
  children,
  options,
}: GeneratorActionBarProps): JSX.Element {
  const { t } = useT();
  const busy = proposing || saving || locked;

  return (
    <div className="genbar__wrap">
      <div className="studio__actions genbar" role="toolbar" aria-label={t('generator.bar.label')}>
        <button type="button" className="btn btn--primary" disabled={busy} onClick={onPropose}>
          {proposing ? t('generator.bar.proposing') : proposeLabel}
        </button>
        <button type="button" className="btn" disabled={busy || !dirty} onClick={onSave}>
          {saving ? t('generator.bar.saving') : t('generator.bar.save')}
        </button>
        <button type="button" className="btn" disabled={!canGoPrevious || busy} onClick={onPrevious}>
          {t('generator.bar.previous')}
        </button>
        <button type="button" className="btn" disabled={!canGoNext || busy} onClick={onNext}>
          {t('generator.bar.next')}
        </button>
        {children}
      </div>

      <div className="genbar__options" role="group" aria-label={t('generator.bar.automation')}>
        <label className="genbar__auto" title={t('generator.bar.autoProposeTitle')}>
          <input
            type="checkbox"
            checked={autoPropose}
            disabled={locked}
            aria-label={t('generator.bar.autoProposeAria')}
            onChange={(event) => onAutoProposeChange(event.target.checked)}
          />
          {t('generator.bar.autoPropose')}
        </label>
        <label className="genbar__auto" title={t('generator.bar.autoSaveTitle')}>
          <input
            type="checkbox"
            checked={autoSave}
            disabled={locked}
            aria-label={t('generator.bar.autoSaveAria')}
            onChange={(event) => onAutoSaveChange(event.target.checked)}
          />
          {t('generator.bar.autoSave')}
        </label>
        {options}
      </div>
    </div>
  );
}

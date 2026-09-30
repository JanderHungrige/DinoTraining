/**
 * The Prepare flow's steps (doc 89): in order, each marked done, open or a choice, and
 * every one clickable, so an expert can go straight to the step they need.
 */

import type { JSX } from 'react';

import { useT, type Key } from '../../i18n';

export const STEPS = ['audit', 'fix', 'split', 'input', 'balance', 'augment', 'save'] as const;
export type StepId = (typeof STEPS)[number];

/** `unused`: the chosen model does not use this step (doc 107); it says why when opened. */
export type StepStatus = 'done' | 'open' | 'choice' | 'unused';

/** Each step's name, as a catalogue key. */
export const STEP_LABEL: Readonly<Record<StepId, Key>> = {
  audit: 'prepare.step.audit',
  fix: 'prepare.step.fix',
  split: 'prepare.step.split',
  input: 'prepare.step.input',
  balance: 'prepare.step.balance',
  augment: 'prepare.step.augment',
  save: 'prepare.step.save',
};

const STATUS_MARK: Readonly<Record<StepStatus, string>> = { done: '✓', open: '•', choice: '○', unused: '–' };

export function firstOpen(statuses: Readonly<Record<StepId, StepStatus>>): StepId {
  return STEPS.find((step) => statuses[step] === 'open') ?? 'save';
}

export interface StepNavProps {
  readonly current: StepId;
  readonly statuses: Readonly<Record<StepId, StepStatus>>;
  readonly onSelect: (step: StepId) => void;
}

export function StepNav({ current, statuses, onSelect }: StepNavProps): JSX.Element {
  const { t } = useT();
  return (
    <ol className="prep-nav" aria-label={t('prepare.nav.label')}>
      {STEPS.map((step, index) => (
        <li key={step}>
          <button
            type="button"
            className={`prep-nav__step prep-nav__step--${statuses[step]}${step === current ? ' prep-nav__step--current' : ''}`}
            aria-current={step === current ? 'step' : undefined}
            onClick={() => onSelect(step)}
          >
            <span className="prep-nav__mark" aria-hidden="true">
              {STATUS_MARK[statuses[step]]}
            </span>
            {index + 1}. {t(STEP_LABEL[step])}
            {statuses[step] === 'unused' ? t('prepare.nav.unused') : ''}
          </button>
        </li>
      ))}
    </ol>
  );
}

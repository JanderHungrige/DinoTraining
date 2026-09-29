/**
 * The Prepare flow's steps (doc 89): in order, each marked done, open or a choice, and
 * every one clickable, so an expert can go straight to the step they need.
 */

import type { JSX } from 'react';

export const STEPS = ['audit', 'fix', 'split', 'input', 'balance', 'augment', 'save'] as const;
export type StepId = (typeof STEPS)[number];

export type StepStatus = 'done' | 'open' | 'choice';

export const STEP_LABEL: Readonly<Record<StepId, string>> = {
  audit: 'Check the data',
  fix: 'Fix what is safe',
  split: 'Split',
  input: 'What the model sees',
  balance: 'Unequal classes',
  augment: 'Changed copies',
  save: 'Save the recipe',
};

const STATUS_MARK: Readonly<Record<StepStatus, string>> = { done: '✓', open: '•', choice: '○' };

export function firstOpen(statuses: Readonly<Record<StepId, StepStatus>>): StepId {
  return STEPS.find((step) => statuses[step] === 'open') ?? 'save';
}

export interface StepNavProps {
  readonly current: StepId;
  readonly statuses: Readonly<Record<StepId, StepStatus>>;
  readonly onSelect: (step: StepId) => void;
}

export function StepNav({ current, statuses, onSelect }: StepNavProps): JSX.Element {
  return (
    <ol className="prep-nav" aria-label="Preparation steps">
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
            {index + 1}. {STEP_LABEL[step]}
          </button>
        </li>
      ))}
    </ol>
  );
}

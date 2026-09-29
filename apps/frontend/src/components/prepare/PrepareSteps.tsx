/**
 * The Prepare flow's body (doc 89): which step is open, what each step's status is, and
 * the step itself. The open step is the user's pick, or else the first one not done.
 */

import { useState, type JSX } from 'react';

import type { PrepTarget } from '../../api/prep';
import type { AugmentationPlan, BalancePlan, Strategy } from '../../api/prepPlan';
import type { PrepareData } from '../../hooks/usePrepareData';
import { AuditStep } from './AuditStep';
import { AugmentStep } from './AugmentStep';
import { BalanceStep } from './BalanceStep';
import { FixStep } from './FixStep';
import { InputStep } from './InputStep';
import { SaveStep } from './SaveStep';
import { SplitStep } from './SplitStep';
import { STEP_LABEL, StepNav, firstOpen, type StepId, type StepStatus } from './StepNav';

/** The user's choices for one dataset and model (`key`); absent means "as recommended". */
export interface Choices {
  readonly key: string;
  readonly grid?: number | null;
  readonly strategy?: Strategy;
  readonly preset?: string;
}

export interface PrepareStepsProps {
  readonly datasetId: string;
  readonly datasetName: string;
  readonly target: PrepTarget | null;
  readonly data: PrepareData;
  readonly plans: { readonly balance: BalancePlan | null; readonly augmentation: AugmentationPlan | null };
  readonly choices: Choices;
  readonly onChoose: (change: Omit<Choices, 'key'>) => void;
}

export function statusesFor(data: PrepareData, target: string): Record<StepId, StepStatus> {
  const audited = data.audit !== null && data.audit.target === target;
  const saved = data.recipes.some((info) => info.recipe.target === target && info.out_of_date.length === 0);
  return {
    audit: audited ? 'done' : 'open',
    fix: audited && (data.audit?.copy_groups.length ?? 0) + (data.audit?.unreadable.length ?? 0) === 0 ? 'done' : 'choice',
    split: data.split ? 'done' : 'open',
    input: 'choice',
    balance: 'choice',
    augment: 'choice',
    save: saved ? 'done' : 'open',
  };
}

export function PrepareSteps(props: PrepareStepsProps): JSX.Element {
  const { data, target, plans, choices } = props;
  const [stepChoice, setStepChoice] = useState<StepId | ''>('');
  const targetId = target?.id ?? '';
  const statuses = statusesFor(data, targetId);
  const step = stepChoice || firstOpen(statuses);
  const strategy: Strategy = choices.strategy ?? plans.balance?.recommended ?? 'none';
  const preset = choices.preset ?? plans.augmentation?.recommended ?? 'none';
  return (
    <div className="prep-flow">
      <StepNav current={step} statuses={statuses} onSelect={setStepChoice} />
      <div className="prep-flow__body">
        <h3 className="prep-flow__title">{STEP_LABEL[step]}</h3>
        <StepBody {...props} step={step} strategy={strategy} preset={preset} />
      </div>
    </div>
  );
}

function StepBody(props: PrepareStepsProps & { step: StepId; strategy: Strategy; preset: string }): JSX.Element {
  const { datasetId, datasetName, target, data, plans, choices, onChoose, step, strategy, preset } = props;
  const targetId = target?.id ?? '';
  const grid = choices.grid ?? null;
  switch (step) {
    case 'audit':
      return (
        <AuditStep
          audit={data.audit}
          auditing={data.auditing}
          target={targetId}
          targetLabel={target?.label ?? ''}
          onRun={() => data.runAudit(targetId)}
        />
      );
    case 'fix':
      return <FixStep audit={data.audit} state={data.state} busy={data.busy} onFix={data.fix} />;
    case 'split':
      return <SplitStep split={data.split} busy={data.busy} onSplit={(mode) => void data.split_(mode)} />;
    case 'input':
      return <InputStep datasetId={datasetId} target={targetId} grid={grid} onGrid={(g) => onChoose({ grid: g })} />;
    case 'balance':
      return <BalanceStep plan={plans.balance} strategy={strategy} onStrategy={(s) => onChoose({ strategy: s })} />;
    case 'augment':
      return (
        <AugmentStep datasetId={datasetId} target={targetId} plan={plans.augmentation} preset={preset} onPreset={(p) => onChoose({ preset: p })} />
      );
    case 'save':
      return (
        <SaveStep
          datasetId={datasetId}
          datasetName={datasetName}
          choices={{ target: targetId, targetLabel: target?.label ?? targetId, grid, strategy, preset }}
          recipes={data.recipes}
          onSaved={data.reloadRecipes}
        />
      );
  }
}

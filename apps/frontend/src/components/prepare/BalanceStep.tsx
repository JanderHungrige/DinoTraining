/**
 * Step 6: unequal classes (doc 86). The recommendation comes pre-selected, with its reason
 * and what each option would do to this dataset's classes.
 */

import type { JSX } from 'react';

import type { BalancePlan, Strategy } from '../../api/prepPlan';
import { useT } from '../../i18n';
import { OptionList } from './OptionList';
import { richText } from './richText';

export interface BalanceStepProps {
  readonly plan: BalancePlan | null;
  readonly strategy: Strategy;
  readonly onStrategy: (strategy: Strategy) => void;
}

function Classes({ plan, strategy }: { readonly plan: BalancePlan; readonly strategy: Strategy }): JSX.Element {
  const { t } = useT();
  return (
    <table className="prep-table">
      <thead>
        <tr>
          <th>{t('prepare.table.class')}</th>
          <th>{t('prepare.table.examples')}</th>
          <th>{t('prepare.table.pictures')}</th>
          {strategy === 'weighted-loss' && <th>{t('prepare.balance.countsAs')}</th>}
          {strategy === 'balanced-sampling' && <th>{t('prepare.balance.perRound')}</th>}
        </tr>
      </thead>
      <tbody>
        {plan.classes.map((row) => (
          <tr key={row.name}>
            <th scope="row">{row.name}</th>
            <td>{row.examples}</td>
            <td>{row.images}</td>
            {strategy === 'weighted-loss' && <td>{row.weight}×</td>}
            {strategy === 'balanced-sampling' && <td>{row.repeat}×</td>}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export function BalanceStep({ plan, strategy, onStrategy }: BalanceStepProps): JSX.Element {
  const { t } = useT();
  if (!plan) return <p role="status">{t('prepare.balance.counting')}</p>;
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        {t('prepare.balance.why')}
      </p>
      <p className="prep-step__summary">
        {richText(t('prepare.balance.ratio'), { ratio: <strong>{plan.ratio}×</strong> })} {plan.reason}
      </p>
      <OptionList
        name="prep-balance"
        label={t('prepare.balance.label')}
        options={plan.options}
        recommended={plan.recommended}
        value={strategy}
        onChange={onStrategy}
      />
      <Classes plan={plan} strategy={strategy} />
      {plan.warnings.map((warning) => (
        <p key={warning} className="prep-step__note">
          {warning}
        </p>
      ))}
      {!plan.applies_to_training && (
        <p className="prep-step__note">
          {t('prepare.balance.notApplied')}
        </p>
      )}
    </div>
  );
}

/**
 * Step 6: unequal classes (doc 86). The recommendation comes pre-selected, with its reason
 * and what each option would do to this dataset's classes.
 */

import type { JSX } from 'react';

import type { BalancePlan, Strategy } from '../../api/prepPlan';
import { OptionList } from './OptionList';

export interface BalanceStepProps {
  readonly plan: BalancePlan | null;
  readonly strategy: Strategy;
  readonly onStrategy: (strategy: Strategy) => void;
}

function Classes({ plan, strategy }: { readonly plan: BalancePlan; readonly strategy: Strategy }): JSX.Element {
  return (
    <table className="prep-table">
      <thead>
        <tr>
          <th>Class</th>
          <th>Examples</th>
          <th>Pictures</th>
          {strategy === 'weighted-loss' && <th>Counts as</th>}
          {strategy === 'balanced-sampling' && <th>Shown per round</th>}
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
  if (!plan) return <p role="status">Counting the classes…</p>;
  return (
    <div className="prep-step">
      <p className="prep-step__why">
        A model rewards itself for being right often. When one class is far more common, it can look
        accurate while mostly ignoring the rare ones — often the ones that matter.
      </p>
      <p className="prep-step__summary">
        The largest class has <strong>{plan.ratio}×</strong> the examples of the smallest. {plan.reason}
      </p>
      <OptionList
        name="prep-balance"
        label="How to handle unequal classes"
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
          Fine-tuning this model does not apply the choice yet; it is saved in the recipe for when it does.
        </p>
      )}
    </div>
  );
}

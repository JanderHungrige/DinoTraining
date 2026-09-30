/**
 * A model's training parameters (doc 100), rendered from doc 99's catalogue: basic first,
 * the rest behind "Advanced settings", every one with its ? and its default.
 */

import type { JSX } from 'react';

import type { Parameters } from '../../hooks/useParameters';
import { useT } from '../../i18n';
import { ParameterField } from './ParameterField';
import '../../params.css';

export interface ParameterFormProps {
  readonly params: Parameters;
  /** A recipe is chosen: fields it sets (the split) are shown but not editable. */
  readonly recipeChosen?: boolean;
  readonly disabled?: boolean;
}

export function ParameterForm({ params, recipeChosen = false, disabled = false }: ParameterFormProps): JSX.Element {
  const { t } = useT();
  const { set } = params;
  if (!set) {
    return (
      <p className="trainer__dim">
        {params.error ? t('training.params.loadFailed', { error: params.error }) : t('training.params.loading')}
      </p>
    );
  }
  const field = (key: string): JSX.Element => {
    const parameter = set.parameters.find((p) => p.key === key)!;
    return (
      <ParameterField
        key={key}
        parameter={parameter}
        value={params.values[key] ?? parameter.default}
        changed={key in params.overrides}
        problem={params.invalid[key] ?? ''}
        setByRecipe={recipeChosen && parameter.recipe_overrides}
        disabled={disabled}
        onChange={(value) => params.change(key, value)}
        onReset={() => params.reset(key)}
      />
    );
  };
  const basic = set.parameters.filter((p) => p.level === 'basic');
  const advanced = set.parameters.filter((p) => p.level === 'advanced');
  const changedAdvanced = advanced.filter((p) => p.key in params.overrides).length;
  const anyChanged = Object.keys(params.overrides).length > 0;

  return (
    <fieldset className="params" disabled={disabled}>
      <legend>{t('training.params.legend', { title: set.title })}</legend>
      <div className="params__grid">{basic.map((p) => field(p.key))}</div>
      {advanced.length > 0 && (
        <details className="params__advanced">
          <summary>
            {changedAdvanced > 0
              ? t('training.params.advancedChanged', { count: changedAdvanced })
              : t('training.params.advanced')}
          </summary>
          <div className="params__grid">{advanced.map((p) => field(p.key))}</div>
        </details>
      )}
      {anyChanged && (
        <button type="button" className="btn btn--small" onClick={params.resetAll}>
          {t('training.params.resetAll')}
        </button>
      )}
    </fieldset>
  );
}

/** The first field that cannot be sent, for the note beside Start — or ''. */
export function blockingParameter(params: Parameters): string {
  const key = Object.keys(params.invalid)[0];
  if (!key) return '';
  const parameter = params.set?.parameters.find((p) => p.key === key);
  return parameter ? `${parameter.label}: ${params.invalid[key]}` : '';
}

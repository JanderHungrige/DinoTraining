/**
 * One parameter row (doc 100): "Plain name (technical term)", the ?, the input, and —
 * when it differs from the default — a mark and a reset.
 *
 * A number field keeps what is being typed as text. "1e-" or "0." is on its way to being
 * a number, and forcing it through `Number()` on every key would wipe it; the value is
 * committed whenever the text parses.
 */

import { useEffect, useId, useState, type JSX } from 'react';

import type { ParameterInfo, ParameterValue } from '../../api/parameters';
import { useT, type Translator } from '../../i18n';
import { HelpPopover } from './HelpPopover';

export interface ParameterFieldProps {
  readonly parameter: ParameterInfo;
  readonly value: ParameterValue;
  readonly changed: boolean;
  readonly problem: string;
  /** A chosen recipe sets this one (doc 99's `recipe_overrides`). */
  readonly setByRecipe: boolean;
  readonly disabled: boolean;
  readonly onChange: (value: ParameterValue) => void;
  readonly onReset: () => void;
}

export function formatValue(parameter: ParameterInfo, value: ParameterValue, { t }: Translator): string {
  if (parameter.kind === 'bool') return t(value ? 'training.params.on' : 'training.params.off');
  if (parameter.kind === 'choice') {
    return parameter.choices.find((c) => c.value === value)?.label ?? String(value);
  }
  return String(value);
}

function parse(text: string): number {
  return text.trim() === '' ? Number.NaN : Number(text);
}

/** NaN equals NaN here: a cleared field and an unparsable one are both "not a number yet". */
function same(a: number, b: ParameterValue): boolean {
  return typeof b === 'number' && (a === b || (Number.isNaN(a) && Number.isNaN(b)));
}

function NumberInput(props: {
  readonly id: string;
  readonly parameter: ParameterInfo;
  readonly value: ParameterValue;
  readonly describedBy: string;
  readonly disabled: boolean;
  readonly onChange: (value: number) => void;
}): JSX.Element {
  const [draft, setDraft] = useState(String(props.value));
  // A reset or another outside change replaces what was being typed; the user's own
  // half-typed "1e-" (the same NaN the field already holds) does not.
  useEffect(() => {
    setDraft((current) => (same(parse(current), props.value) ? current : String(props.value)));
  }, [props.value]);
  return (
    <input
      id={props.id}
      type="text"
      inputMode="decimal"
      className="param-field__input"
      value={draft}
      disabled={props.disabled}
      aria-describedby={props.describedBy}
      onChange={(event) => {
        setDraft(event.target.value);
        props.onChange(parse(event.target.value));
      }}
    />
  );
}

function Input(props: {
  readonly id: string;
  readonly parameter: ParameterInfo;
  readonly value: ParameterValue;
  readonly describedBy: string;
  readonly disabled: boolean;
  readonly onChange: (value: ParameterValue) => void;
}): JSX.Element {
  const { parameter, value } = props;
  if (parameter.kind === 'bool') {
    return (
      <input
        id={props.id}
        type="checkbox"
        checked={Boolean(value)}
        disabled={props.disabled}
        aria-describedby={props.describedBy}
        onChange={(event) => props.onChange(event.target.checked)}
      />
    );
  }
  if (parameter.kind === 'choice') {
    return (
      <select
        id={props.id}
        value={String(value)}
        disabled={props.disabled}
        aria-describedby={props.describedBy}
        onChange={(event) => props.onChange(event.target.value)}
      >
        {parameter.choices.map((choice) => (
          <option key={choice.value} value={choice.value}>
            {choice.label}
          </option>
        ))}
      </select>
    );
  }
  return <NumberInput {...props} />;
}

export function ParameterField(props: ParameterFieldProps): JSX.Element {
  const { parameter, value, changed, problem, setByRecipe } = props;
  const translator = useT();
  const { t } = translator;
  const id = useId();
  const described = `${id}-about`;
  const defaultText = formatValue(parameter, parameter.default, translator);
  return (
    <div className={`param-field${changed ? ' param-field--changed' : ''}`}>
      <label className="param-field__label" htmlFor={id}>
        {parameter.label}
        {/* German names the English term itself (Jan, 2026-09-30): "Epochs (epochs)" says it twice. */}
        {parameter.term.toLowerCase() !== parameter.label.toLowerCase() && (
          <> <span className="param-field__term">({parameter.term})</span></>
        )}
      </label>
      <HelpPopover label={parameter.label} help={parameter.help} defaultText={defaultText} why={parameter.why} />
      <Input
        id={id}
        parameter={parameter}
        value={value}
        describedBy={described}
        disabled={props.disabled || setByRecipe}
        onChange={props.onChange}
      />
      <span id={described} className="visually-hidden">
        {parameter.help} {t('training.params.defaultSentence', { value: defaultText })}
      </span>
      {changed && !setByRecipe && (
        <button
          type="button"
          className="param-field__reset"
          aria-label={t('training.params.resetOne', { label: parameter.label, value: defaultText })}
          title={t('training.params.backToDefault', { value: defaultText })}
          onClick={props.onReset}
        >
          {t('training.params.changed')} ↺
        </button>
      )}
      {setByRecipe && <span className="param-field__note">{t('training.params.setByRecipe')}</span>}
      {problem && !setByRecipe && (
        <span className="param-field__problem" role="alert">
          {problem}
        </span>
      )}
    </div>
  );
}

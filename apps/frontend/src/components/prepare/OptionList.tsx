/**
 * A choice between explained options, one of them recommended (doc 89): every step's
 * default is visible as a default, and every alternative says what it does.
 */

import type { JSX } from 'react';

export interface Option<T extends string> {
  readonly id: T;
  readonly title: string;
  readonly explained: string;
  readonly badges?: readonly string[];
}

export interface OptionListProps<T extends string> {
  readonly name: string;
  readonly label: string;
  readonly options: readonly Option<T>[];
  readonly recommended: string;
  readonly value: string;
  readonly onChange: (value: T) => void;
}

export function OptionList<T extends string>(props: OptionListProps<T>): JSX.Element {
  const { name, label, options, recommended, value, onChange } = props;
  return (
    <div className="prep-options" role="radiogroup" aria-label={label}>
      {options.map((option) => (
        <label key={option.id} className="prep-option">
          <input
            type="radio"
            name={name}
            value={option.id}
            checked={value === option.id}
            onChange={() => onChange(option.id)}
          />
          <span className="prep-option__title">
            {option.title}
            {option.id === recommended && <span className="badge">recommended</span>}
            {option.badges?.map((badge) => (
              <span key={badge} className="badge">
                {badge}
              </span>
            ))}
          </span>
          <span className="prep-option__explained">{option.explained}</span>
        </label>
      ))}
    </div>
  );
}

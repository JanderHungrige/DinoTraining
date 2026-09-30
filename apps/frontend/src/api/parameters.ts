/**
 * Every training knob a model honours (doc 99). Mirrors
 * backend/app/api/v1/training_parameters.py.
 */

import { apiFetch } from './client';
import { arrayOf, hasFields } from './prepGuards';

export type ParameterValue = number | boolean | string;

export interface ParameterChoice {
  readonly value: string;
  readonly label: string;
}

export interface ParameterInfo {
  readonly key: string;
  /** The plain name, read first: "Rounds". */
  readonly label: string;
  /** The technical term, shown in brackets: "epochs". */
  readonly term: string;
  readonly help: string;
  readonly default: ParameterValue;
  /** Why the default is what it is. */
  readonly why: string;
  readonly kind: 'int' | 'float' | 'bool' | 'choice';
  readonly level: 'basic' | 'advanced';
  readonly minimum: number | null;
  readonly maximum: number | null;
  readonly choices: readonly ParameterChoice[];
  /** A chosen recipe's value replaces this one (the split lives there). */
  readonly recipe_overrides: boolean;
}

export interface ParameterSetInfo {
  readonly family: string;
  readonly title: string;
  readonly covers: string;
  readonly parameters: readonly ParameterInfo[];
}

const isParameter = (v: unknown): v is ParameterInfo =>
  hasFields(v, {
    key: 'string',
    label: 'string',
    term: 'string',
    help: 'string',
    why: 'string',
    kind: 'string',
    level: 'string',
    choices: 'array',
    recipe_overrides: 'boolean',
  });

export const isParameterSet = (v: unknown): v is ParameterSetInfo =>
  hasFields(v, { family: 'string', title: 'string', parameters: 'array' }) &&
  arrayOf(isParameter)((v as { parameters: unknown }).parameters);

export function getParameters(modelId: string): Promise<ParameterSetInfo> {
  return apiFetch(`/training/parameters/${encodeURIComponent(modelId)}`, isParameterSet);
}

/** Why a value cannot be sent, or '' when it can. The backend says the same (422). */
export function problemWith(parameter: ParameterInfo, value: ParameterValue): string {
  if (parameter.kind === 'bool' || parameter.kind === 'choice') return '';
  if (typeof value !== 'number' || Number.isNaN(value)) return 'Enter a number.';
  if (parameter.kind === 'int' && !Number.isInteger(value)) return 'Enter a whole number.';
  const { minimum: low, maximum: high } = parameter;
  if ((low !== null && value < low) || (high !== null && value > high)) {
    return `Between ${low ?? 'any'} and ${high ?? 'any'}.`;
  }
  return '';
}

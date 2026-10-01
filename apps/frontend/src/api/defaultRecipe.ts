/**
 * The default recipe for a model (doc 101). Mirrors backend/app/api/v1/prep_default_recipe.py.
 */

import { apiFetch } from './client';
import type { Recipe } from './prepPlan';
import { datasetPath, hasFields, jsonBody } from './prepGuards';

/** Which model: "head" with its head type and backbone, or a fine-tune id. */
export interface ModelRef {
  readonly model_id: string;
  readonly head_type_id?: string;
  readonly backbone_id?: string;
}

export interface DefaultRecipeJob {
  readonly job_id: string;
  readonly state: string;
  /** The step running now, in plain words; the result or the refusal once finished. */
  readonly message: string;
  readonly recipe: Recipe | null;
}

export interface TargetInfo {
  readonly target: string;
  readonly label: string;
}

const isJob = (v: unknown): v is DefaultRecipeJob =>
  hasFields(v, { job_id: 'string', state: 'string', message: 'string', recipe: 'object?' });

export function startDefaultRecipe(datasetId: string, model: ModelRef): Promise<DefaultRecipeJob> {
  return apiFetch(datasetPath(datasetId, 'recipes/default'), isJob, jsonBody(model));
}

export function getDefaultRecipeJob(jobId: string): Promise<DefaultRecipeJob> {
  return apiFetch(`/prep/default-recipes/${encodeURIComponent(jobId)}`, isJob);
}

export function resolveTarget(model: ModelRef): Promise<TargetInfo> {
  const query = new URLSearchParams(
    Object.entries(model).filter((entry): entry is [string, string] => typeof entry[1] === 'string' && entry[1] !== ''),
  );
  return apiFetch(`/prep/targets/resolve?${query.toString()}`, (v: unknown): v is TargetInfo =>
    hasFields(v, { target: 'string', label: 'string' }),
  );
}

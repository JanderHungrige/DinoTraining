/**
 * Prepare data, second half: model input, balance, augmentation and recipes
 * (docs 85–88). Mirrors backend/app/api/v1/prep_input.py, prep_balance.py,
 * prep_augment.py and prep_recipes.py.
 */

import { apiFetch } from './client';
import { arrayOf, datasetPath, hasFields, isRecord, jsonBody } from './prepGuards';

export interface ObjectSizes {
  readonly median_px: number;
  readonly p10_px: number;
  readonly needed_px: number;
  readonly too_small_share: number;
}

export interface InputPlan {
  readonly target: string;
  readonly label: string;
  readonly input_size: number;
  readonly fit: string;
  readonly fit_explained: string;
  readonly normalisation: string;
  readonly masks: string | null;
  readonly padding_share: number;
  readonly objects: ObjectSizes | null;
  readonly tiling: {
    readonly recommended: boolean;
    readonly columns: number;
    readonly rows: number;
    readonly objects_after: ObjectSizes | null;
    readonly supported: boolean;
    readonly reason: string;
  };
}

export interface PreviewImage {
  readonly path: string;
  readonly tile: readonly [number, number, number, number] | null;
  readonly data_url: string;
  readonly width: number;
  readonly height: number;
  readonly objects: number;
  readonly lost: number;
  readonly too_small: number;
}

export interface InputPreview {
  readonly plan: InputPlan;
  readonly colours: Readonly<Record<string, string>>;
  readonly images: readonly PreviewImage[];
  readonly skipped: readonly string[];
}

export type Strategy = 'none' | 'weighted-loss' | 'balanced-sampling';

export interface BalancePlan {
  readonly ratio: number;
  readonly recommended: Strategy;
  readonly reason: string;
  readonly classes: readonly {
    readonly name: string;
    readonly examples: number;
    readonly images: number;
    readonly weight: number;
    readonly repeat: number;
  }[];
  readonly options: readonly { readonly id: Strategy; readonly title: string; readonly explained: string }[];
  readonly warnings: readonly string[];
  readonly applies_to_training: boolean;
}

export interface AugmentationPlan {
  readonly recommended: string;
  readonly reason: string;
  readonly presets: readonly {
    readonly id: string;
    readonly title: string;
    readonly explained: string;
    readonly guarded: boolean;
  }[];
  readonly guarded_classes: readonly string[];
  readonly applies_to_training: boolean;
}

export interface AugmentationPreview {
  readonly preset: string;
  readonly images: readonly PreviewImage[];
  readonly guarded_classes: readonly string[];
}

export interface Recipe {
  readonly id: string;
  readonly name: string;
  readonly version: number;
  readonly created_at: string;
  readonly target: string;
  readonly excluded: number;
  readonly split: { readonly seed: number; readonly sides: Readonly<Record<string, number>>; readonly buffer: number };
  readonly fit: string;
  readonly input_size: number;
  readonly tiling: { readonly columns: number; readonly rows: number } | null;
  readonly imbalance: Strategy;
  readonly augmentation: string;
  readonly augment_copies: number;
  readonly open_problems: readonly string[];
}

export interface RecipeInfo {
  readonly recipe: Recipe;
  readonly out_of_date: readonly string[];
}

export interface RecipeRequest {
  readonly name: string;
  readonly target: string;
  readonly imbalance: Strategy;
  readonly augmentation: string;
  readonly grid?: number | null;
}

const isPlan = (v: unknown): v is InputPlan =>
  hasFields(v, { target: 'string', fit: 'string', fit_explained: 'string', input_size: 'number', tiling: 'object' });

const isPreviewImage = (v: unknown): v is PreviewImage =>
  hasFields(v, { path: 'string', data_url: 'string', width: 'number', height: 'number', too_small: 'number' });

const isInputPreview = (v: unknown): v is InputPreview =>
  hasFields(v, { plan: 'object', colours: 'object', images: 'array', skipped: 'array' }) &&
  isRecord(v) &&
  isPlan(v['plan']) &&
  (v['images'] as unknown[]).every(isPreviewImage);

const isBalance = (v: unknown): v is BalancePlan =>
  hasFields(v, { ratio: 'number', recommended: 'string', reason: 'string', classes: 'array', options: 'array' });

const isAugmentationPlan = (v: unknown): v is AugmentationPlan =>
  hasFields(v, { recommended: 'string', reason: 'string', presets: 'array', guarded_classes: 'array' });

const isAugmentationPreview = (v: unknown): v is AugmentationPreview =>
  hasFields(v, { preset: 'string', images: 'array' }) &&
  isRecord(v) &&
  (v['images'] as unknown[]).every(isPreviewImage);

const isRecipeInfo = (v: unknown): v is RecipeInfo =>
  hasFields(v, { recipe: 'object', out_of_date: 'array' }) &&
  isRecord(v) &&
  hasFields(v['recipe'], { id: 'string', name: 'string', version: 'number', split: 'object' });

function query(target: string, grid?: number | null): string {
  const params = new URLSearchParams({ target });
  if (grid) params.set('grid', String(grid));
  return params.toString();
}

export function getInputPlan(datasetId: string, target: string, grid?: number | null): Promise<InputPlan> {
  return apiFetch(`${datasetPath(datasetId, 'input-plan')}?${query(target, grid)}`, isPlan);
}

export function previewInput(
  datasetId: string,
  target: string,
  grid: number | null,
  count = 6,
): Promise<InputPreview> {
  return apiFetch(datasetPath(datasetId, 'input-preview'), isInputPreview, jsonBody({ target, grid, count }));
}

export function getBalance(datasetId: string, target: string): Promise<BalancePlan> {
  return apiFetch(`${datasetPath(datasetId, 'balance')}?${query(target)}`, isBalance);
}

export function getAugmentation(datasetId: string, target: string): Promise<AugmentationPlan> {
  return apiFetch(`${datasetPath(datasetId, 'augmentation')}?${query(target)}`, isAugmentationPlan);
}

export function previewAugmentation(
  datasetId: string,
  target: string,
  preset: string,
  count = 3,
): Promise<AugmentationPreview> {
  return apiFetch(
    datasetPath(datasetId, 'augmentation-preview'),
    isAugmentationPreview,
    jsonBody({ target, preset, count }),
  );
}

export function saveRecipe(datasetId: string, request: RecipeRequest): Promise<RecipeInfo> {
  return apiFetch(datasetPath(datasetId, 'recipes'), isRecipeInfo, jsonBody(request));
}

export function listRecipes(datasetId: string): Promise<RecipeInfo[]> {
  return apiFetch(datasetPath(datasetId, 'recipes'), arrayOf(isRecipeInfo));
}

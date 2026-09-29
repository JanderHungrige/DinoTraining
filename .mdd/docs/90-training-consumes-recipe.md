---
id: 90-training-consumes-recipe
title: Training Consumes the Recipe — Split, Fixes, Tiles, Balance and a Test Score
edition: DinoTraining
depends_on: [11-training-job, 44-rfdetr-finetune, 83-safe-fixes, 84-leakage-safe-split, 85-model-input-planning, 86-imbalance-strategy, 87-augmentation-presets, 88-preparation-recipe, 89-guided-preparation-flow]
relates: [12-head-instance-registry, 49-osdar23-rail, 62-tiled-inference, 91-preparation-for-agents]
source_files:
  - backend/app/ml/training/sample_prep.py
  - backend/app/ml/training/samples.py
  - backend/app/ml/training/vocabulary.py
  - backend/app/ml/training/tiles.py
  - backend/app/ml/training/loop.py
  - backend/app/ml/training/live_loop.py
  - backend/app/ml/training/augmented.py
  - backend/app/ml/training/preparation.py
  - backend/app/ml/training/runner.py
  - backend/app/ml/training/config.py
  - backend/app/ml/training/job.py
  - backend/app/ml/training/persist.py
  - backend/app/ml/foundation/finetune.py
  - backend/app/datasets/tiling.py
  - backend/app/datasets/store.py
  - backend/app/prep/input_plan.py
  - backend/app/prep/recipe_use.py
  - backend/app/api/v1/training.py
  - backend/app/api/v1/foundation_finetune.py
  - apps/frontend/src/api/training.ts
  - apps/frontend/src/hooks/useRecipeChoice.ts
  - apps/frontend/src/components/RecipePicker.tsx
  - apps/frontend/src/components/TrainingProgress.tsx
  - apps/frontend/src/components/prepare/SaveStep.tsx
  - apps/frontend/src/components/prepare/PrepareSteps.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/tabs/PrepareTab.tsx
  - apps/frontend/src/types/navigation.ts
  - apps/frontend/src/App.tsx
routes:
  - POST /api/v1/training/jobs (field `recipe_id`; job `test_metrics`, `recipe_id`)
  - POST /api/v1/foundation/finetune (field `recipe_id`)
models: []
test_files:
  - backend/tests/test_training_recipe.py
  - backend/tests/test_training_recipe_api.py
  - apps/frontend/src/tabs/HeadTrainerTab.recipe.test.tsx
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [training, recipe, split, tiling, class-map, exclusions, test-metrics, provenance]
path: Training/Recipe
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts: []
satisfies_contracts:
  - from: 83-safe-fixes
    function: "training reads images.excluded and prep_state.class_map"
    when: "whenever samples are built for training or fine-tuning"
    status: done
    verified_at: "backend/app/ml/training/samples.py:build_samples"
  - from: 84-leakage-safe-split
    function: "training uses images.split instead of shuffling"
    when: "a run names a recipe"
    status: done
    verified_at: "backend/app/ml/training/preparation.py:choose_split"
  - from: 85-model-input-planning
    function: "training cuts the planned tile grid"
    when: "a recipe carries a recommended tiling"
    status: done
    verified_at: "backend/app/ml/training/tiles.py:tile_samples"
  - from: 88-preparation-recipe
    function: "training accepts a recipe id, refuses an out-of-date one, applies it, records it"
    when: "a training or fine-tuning run is started with a recipe"
    status: done
    verified_at: "backend/app/prep/recipe_use.py:resolve_recipe"
  - from: 89-guided-preparation-flow
    function: "a 'Train with this recipe' action"
    when: "a recipe is saved and up to date"
    status: done
    verified_at: "apps/frontend/src/components/prepare/SaveStep.tsx:TrainButton"
known_issues:
  - "Fine-tuning (RF-DETR) applies the recipe's split, exclusions and class map, but not its imbalance strategy, augmentation or tiles. The Balance and Augment steps say so for fine-tune targets."
  - "A recipe describes one dataset. A run on several datasets cannot use recipes yet (422 with the reason)."
  - "The Generator's datasets do not get a recipe made for them automatically: its conventions are known, but the audit and split still have to run. A one-click 'prepare with the recommendations' is a natural next step (and useful to agents, doc 91)."
  - "Doc 49's and Wave 7's rail numbers (0.5–0.6 for a head, 0.96 for RF-DETR) were measured on random splits. On OSDaR's leak-free split a DINOv2-small head reaches 0.016 in 6 epochs. Re-run the rail comparisons with a recipe before quoting them again."
  - "The recipe picker sits above the dataset list in the Training tab, because the form's Start button is at the bottom of it. It only appears once a single dataset is chosen."
security_read_sites: []
sister_projects: []
---

# 90 — Training Consumes the Recipe

## Purpose

Docs 81–89 decide how a dataset should be prepared. This makes training do it, and
makes a trained head able to say how its data was prepared.

## What every run now honours

With or without a recipe, `build_samples` (through `sample_prep.py`) applies the Fix
step's decisions. The user made those explicitly and was told training would honour
them:

- **Excluded images** are left out.
- **The class map** renames and merges classes.
- **A class left out** has its boxes and masks turned into **ignore** regions, not
  background. Background would teach the model that those objects are background.

## What a recipe adds

`recipe_id` on a training or fine-tuning request:

| Part | Effect |
|---|---|
| split | the stored split replaces `split_indices` (buffer frames train nowhere) |
| tiles | each picture is cut into the planned grid (`tiles.py`, below) |
| imbalance, augmentation | set on the config (docs 86, 87) |
| `recipe_id` | recorded in the config, which is saved with the head (provenance, doc 12) |

**Refusals:**

| Case | Status | Reason given |
|---|---|---|
| unknown recipe | 404 | — |
| out of date | 409 | what changed (doc 88's check) |
| prepared for another kind of model | 422 | "prepared for …, not a detection model" |
| more than one dataset | 422 | a recipe describes one dataset |

**Without a recipe** the run still works. Its `notes` then carry the "unprepared data"
warning: pictures were split at random, and the score may look better than the model is.

## Tiles

`tile_samples` cuts every detection sample with `grid_for` and `plan_tiles`, the
definitions the preview (doc 85) and tiled inference (doc 62) use. In each tile:
- a box at least half inside is a clipped target;
- a box less than half inside is an ignore region;
- empty tiles are kept at `DEFAULT_BACKGROUND_RATIO` per useful tile (doc 49's
  measurement).

A tile carries its crop (`TrainingSample.crop`), and `load_sample_image` is the one
loader, used by the cache, the live pass and the augmented copies. Segmentation samples
stay whole.

## The test score

Until now `split.test` was computed and never used. The runner now:
1. leaves the loop on early stopping instead of finishing there;
2. scores the **best** weights once on the test side (`score_test`), through the same
   evaluator as validation;
3. reports `test_metrics` on the job;
4. saves them with the head as `test_*` metrics.

The Training tab shows them as "the honest number".

## Frontend

- **Training tab:** a recipe picker preselects the latest recipe that still describes the
  data (a default derived from the loaded list; "none" is an explicit choice). Without a
  recipe it warns.
- **Save step (doc 89):** "Train with <recipe>" opens Training at that dataset and
  recipe, the same way the Generator opens Inspect (doc 74).

## Verified live (2026-09-30)

**Blood cells, recipe "blood v1"** (stored split 253/75/36, weighted loss, microscopy
copies), DINOv2-small detection head, 8 epochs, 327 s:
- **best validation mAP 0.498; test mAP 0.412** (mAP50 0.647, mAP75 0.177);
- no "unprepared" note, since a recipe was used.

The test score is lower than the validation score, as it should be: validation chose the
epoch, and the test pictures had no say.

**OSDaR23 train (temporal), recipe "osdar tiled":** the plan's 5×5 tiles, DINOv2-small
detection head. The job reported "312 pictures became 1068 tiles".

Both runs used the same stored split (211/78/23), 6 epochs, and the corrected metric (doc 11,
Bugs):

| | Tiles | Time | Best val mAP | mAP50 by epoch |
|---|---|---|---|---|
| whole pictures (`grid: 1`) | — | 90 s | 0.007 | 0.014 0.000 0.000 0.000 0.001 0.005 |
| 5×5 tiles (the plan) | 1,068 | 356 s | **0.016** | 0.019 0.014 **0.033** 0.007 0.007 0.007 |

- **Tiling helps as planned,** 2–3× on every measure.
- **Both are low,** and that is the finding, not a bug. With the leak-free split this data
  has 58 groups, and neither run learns much in 6 epochs.
- **Tiles checked by eye:** they are cut correctly, and their boxes match the source,
  which itself places some boxes on the pole rather than on the light.
- **No test score, and the job said why.** The test side held no objects, and the job
  reported that instead of a misleading 0.0.

Two bugs came out of this run, both fixed:
- **mAP counted absent classes as 0** (doc 11). Under the old metric the same runs read
  0.004 and 0.001.
- **An empty test side scored 0.0.

**In the browser:** Save step → "Train with blood v1 · v1" → the Training tab opens with
Blood cells chosen and the recipe preselected, explained underneath.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

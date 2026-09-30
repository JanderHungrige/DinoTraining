---
id: 101-default-recipes
title: Default Recipes — What a Recipe Is, and One Click to the Model's Default
edition: DinoTraining
depends_on: [88-preparation-recipe, 84-leakage-safe-split, 86-imbalance-strategy, 87-augmentation-presets, 81-dataset-audit, 99-parameter-catalogue]
relates: [100-parameter-form, 102-training-knobs-for-agents, 89-guided-preparation-flow, 97-finetune-ui]
source_files:
  - backend/app/prep/default_recipe.py
  - backend/app/prep/profiles.py
  - backend/app/api/v1/prep_default_recipe.py
  - backend/app/api/v1/router.py
  - backend/app/prep/split_service.py
  - apps/frontend/src/api/defaultRecipe.ts
  - apps/frontend/src/hooks/useDefaultRecipe.ts
  - apps/frontend/src/hooks/useRecipeChoice.ts
  - apps/frontend/src/components/RecipeExplainer.tsx
  - apps/frontend/src/components/RecipePicker.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/components/finetune/FoundationFinetunePanel.tsx
  - apps/frontend/src/App.tsx
  - apps/frontend/src/params.css
routes:
  - GET /api/v1/prep/targets/resolve
  - POST /api/v1/datasets/{dataset_id}/recipes/default
  - GET /api/v1/prep/default-recipes/{job_id}
models: []
test_files:
  - backend/tests/test_default_recipe.py
  - backend/tests/test_prep_split_api.py
  - apps/frontend/src/components/RecipeExplainer.test.tsx
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [recipe, preparation, defaults, onboarding, non-experts, training, fine-tuning]
path: Training/Recipes/Default
initiative: dinotraining
wave: dinotraining-wave-13
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 101 — Default Recipes

## Purpose

Jan (2026-09-30): *"Can you create a default recipe per model? Also explain to the user what
recipes are and how and where to create them. Some users just start, and this leads them back
to the right place."*

**Two gaps:**
- **SAM 2, SAM 3 and the DINO backbones need a recipe** (doc 92's preflight), and a user who
  starts in Training was refused with no way to get one from there.
- **A DINO head without a recipe** trains on a random split. That is the one that lets
  near-identical video frames sit on both sides, which leaked a 0.96 that was really about
  0.5.

## What a "default recipe" is

A recipe holds a dataset's split, so it cannot exist without data. **The default recipe for
a model** therefore means the Prepare data flow run with every recommendation accepted, for
one dataset and one model.

**Steps:**
1. **Audit,** if there is none, or it no longer matches the data, or it judged a different
   model.
2. **Leak-free split,** if there is none, or the audit had to be redone because the data
   changed. The mode is `keep-source` when every picture came with a split from its source,
   and `auto` (scenes and video segments grouped) otherwise.
3. **Class balance and changed copies:** the recommended strategy (doc 86) and preset
   (doc 87).
4. **Tiles:** the input plan's own choice (doc 85).
5. **Save** as **"Default for <model>"**. It is a new version when the name exists, like any
   recipe, so it can be refined in Prepare data afterwards.

**Idempotent:** an up-to-date "Default for <model>" recipe with the same target is returned,
not duplicated.

## Model → profile

`profile_for(model_id, head_type_id, backbone_id)`:

| Model | Profile |
|---|---|
| `head` + a head type's task + backbone family | `head-{task}-{dinov2,dinov3}` |
| `rf-detr-nano/small/base` | same id |
| `sam2.1-hiera-small/base-plus/large` | same id |
| `sam3` | `sam3` |
| `dinov2-*-{classification,segmentation}`, `dinov3-*-…` | `head-{task}-{family}` (same input) |

A depth head has no recipe (there is nothing to split by class), and gets a 422 that says so.

**New profiles:**
- `head-segmentation-dinov3` and `head-classification-dinov3`;
- `rf-detr-small` and `rf-detr-base`;
- `sam2.1-hiera-base-plus` and `sam2.1-hiera-large`;
- **`sam3`:** masks, stretched to 1008 px. Wave 14 adds its phrase checks.

Each profile reads its input size from the installed model's processor, as before.

## API

- **`GET /prep/targets/resolve?model_id=…[&head_type_id=…&backbone_id=…]`** returns
  `{target, label}`. Prepare data is opened at this target.
- **`POST /datasets/{id}/recipes/default`** with `{model_id, head_type_id?, backbone_id?}`
  returns a 202 job (`PrepRunner`, kind `default-recipe`). Its `message` names the step
  running.
- **`GET /prep/default-recipes/{job_id}`** gives the state and `message`, and `recipe` when
  it completes.

**Refusals:**
- an unknown dataset → 404;
- an unknown model or a depth head → 422;
- a dataset without pictures → the job fails with the split's own message.

## UI — "What is a recipe?"

`RecipeExplainer` shows wherever a recipe can be chosen and none is: in the head form under
the recipe picker, and in the fine-tune panel.

**What it says, in plain words:**
- **A recipe is the saved preparation of one dataset for one model.** It records:
  - which pictures train, which pick the best round, and which give the final score (a
    split that keeps near-identical pictures together);
  - class fixes;
  - the input size and tiles;
  - how unequal classes are handled;
  - changed copies.
- **Why it matters:** without one the split is random, and near-identical pictures on both
  sides make the score look better than the model is.
- **Where recipes are made:** Prepare data, step by step.

**Actions:**
- **Create the default recipe** runs the job, shows its step, and then selects the new
  recipe in the picker.
- **Open Prepare data** sets Prepare's remembered dataset and model (doc 69 keys
  `prepare.dataset` / `prepare.target`) and switches tab, so it opens at this dataset and
  model.

## Business Rules

1. **The default never overwrites a user's split without cause.** An existing split is kept
   unless the data changed since the audit.
2. **The recipe is ordinary:** listed, checked for staleness, and editable like one saved by
   hand.
3. **The explainer never blocks.** A head can still train without a recipe; the explainer
   says what that costs.

## Found while building: a kept source split could not make a recipe

- **The bug (Wave 11, doc 84):** `make_split(mode="keep-source")` reported the imported split
  but stored no split settings. A recipe then refused the dataset with *"The dataset has not
  been split yet"*, although every picture was on a side.
- **The fix:** the kept split now records its settings, with the shares taken from the
  sides. A test pins it.

## Verified (2026-09-30)

- **Tests:** backend 1720 green, frontend 995 green; ruff, mypy app and tsc are clean.
- **Running app, Training → Fine-tune → RF-DETR (nano) on "Wave 11 intake check" (no
  recipe):**
  - The explainer showed under the recipe picker.
  - **Create the default recipe** saved and selected *"Default for RF-DETR (nano) · v1"* in
    about a second: the imported split kept (16/3/1), weighted loss, the indoor preset.
  - The preflight then passed its recipe check.
- **With SAM 2.1 chosen:**
  - The heading read *"What is a recipe? This model needs one."*
  - **Open Prepare data** opened Prepare at "Wave 9 autoplay check" and "Fine-tune SAM 2.1
    (small)".

## Bugs

(none yet)

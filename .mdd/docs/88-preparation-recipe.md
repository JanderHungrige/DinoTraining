---
id: 88-preparation-recipe
title: Preparation Recipe — A Saved, Versioned Record of How the Data Was Prepared
edition: DinoTraining
depends_on: [81-dataset-audit, 83-safe-fixes, 84-leakage-safe-split, 85-model-input-planning, 86-imbalance-strategy, 87-augmentation-presets]
relates: [12-head-provenance, 89-guided-preparation-flow, 90-training-consumes-recipe, 91-preparation-for-agents]
source_files:
  - backend/app/prep/recipe.py
  - backend/app/prep/split_service.py
  - backend/app/prep/audit.py
  - backend/app/api/v1/prep_recipes.py
  - backend/app/api/v1/router.py
routes:
  - POST /api/v1/datasets/{dataset_id}/recipes
  - GET /api/v1/datasets/{dataset_id}/recipes
  - GET /api/v1/datasets/{dataset_id}/recipes/{recipe_id}
models:
  - <dataset>/recipes/<id>.json
  - <dataset>/split.json (how the stored split was made)
test_files:
  - backend/tests/test_prep_recipe_api.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, recipe, reproducibility, provenance, versioning, non-experts]
path: Prepare Data/Recipe
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts:
  - function: "training accepts a recipe id, refuses an out-of-date one with its reasons, applies split, class map, tiling, imbalance and augmentation, and records the recipe id in the head's provenance"
    when: "a training or fine-tuning run is started with a recipe"
    satisfied_by: 90-training-consumes-recipe
satisfies_contracts: []
known_issues:
  - "Splits made before 2026-09-30 have no split.json, so a recipe refuses them until the Split step is run again. That is deliberate: without the seed and shares the split cannot be made again."
  - "A recipe covers one dataset. Training on several datasets at once (doc 11 allows it) takes one recipe per dataset; doc 90 decides how they combine."
security_read_sites: []
sister_projects: []
---

# 88 — Preparation Recipe

## Purpose

Everything the Prepare steps decide has to reach training intact, and a trained head
has to be able to say how its data was prepared. The recipe is that record:
- saved with the dataset;
- never edited;
- versioned by name;
- able to tell when the data no longer matches it.

## What a recipe holds

| Part | From | Why |
|---|---|---|
| `facts_hash` | the audit's hash of the data as training sees it (doc 81), which includes exclusions and the class map (doc 83) | detects any change to images, annotations or fixes |
| `class_map`, `excluded` | doc 83 | training applies the map; the count is for people |
| `split` | mode, seed, shares (`split.json`, new), sides, buffer, and a fingerprint of the stored assignment | the same recipe gives the same split, and a changed split is noticed |
| `fit`, `input_size`, `tiling` | doc 85's plan (`grid` overrides it) | training cuts the same tiles the preview showed |
| `imbalance`, `augmentation`, `augment_copies` | docs 86, 87 | `training_fields()` gives them as training request fields |
| `open_problems` | the audit's `problem` findings, by title | saved knowingly, shown with the recipe |

## Rules

1. **Each step first:**
   - No audit → 409, "Run the Audit step first".
   - The data changed since the audit → 409, "Run the audit again".
   - No split (or a split without `split.json`) → 409, "Run the Split step first".
   - An unknown target, strategy or preset → 422.
2. **Never edited.** Saving under an existing name writes version n + 1, with a new id.
3. **Out of date is a state.** `GET` returns `out_of_date` reasons: the class map
   changed, images, annotations or exclusions changed, or the split changed. Undoing a
   change makes the recipe valid again, because it is compared by content, not by time.
   Training (doc 90) refuses an out-of-date recipe with those reasons.

## Verified

Tested through the ASGI app:
- the refusal order;
- a saved recipe's contents (seed, sides summing to the dataset, fit and size for the
  target, strategy and preset);
- versioning by name;
- the out-of-date cycle: exclude → out of date, include → valid again, re-split → out
  of date with the split reason.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

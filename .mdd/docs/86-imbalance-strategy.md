---
id: 86-imbalance-strategy
title: Imbalance Strategy — Weighted Loss or Balanced Sampling, Chosen From the Numbers
edition: DinoTraining
depends_on: [11-training-job, 81-dataset-audit, 83-safe-fixes]
relates: [11-training-job, 43-dense-detector, 81-dataset-audit, 88-preparation-recipe, 89-guided-preparation-flow, 90-training-consumes-recipe]
source_files:
  - backend/app/ml/training/imbalance.py
  - backend/app/ml/training/losses.py
  - backend/app/ml/training/loop.py
  - backend/app/ml/training/runner.py
  - backend/app/ml/training/config.py
  - backend/app/api/v1/training.py
  - backend/app/prep/balance_plan.py
  - backend/app/api/v1/prep_balance.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/datasets/{dataset_id}/balance
  - POST /api/v1/training/jobs (new field `imbalance`)
models: []
test_files:
  - backend/tests/test_training_imbalance.py
  - backend/tests/test_prep_balance.py
data_flow: reads-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, class-imbalance, weighted-loss, repeat-factor-sampling, training, non-experts]
path: Prepare Data/Balance
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts:
  - function: "fine-tuning (RF-DETR, SAM) applies the recipe's imbalance strategy"
    when: "a recipe for a fine-tune target carries one"
    satisfied_by: 90-training-consumes-recipe
satisfies_contracts: []
known_issues:
  - "Head training applies the strategy. Fine-tuning (RF-DETR, SAM) does not yet; the plan says so (`applies_to_training: false`). Doc 90 closes it."
  - "Detection reports mean AP only, so the effect on one class is visible only through the mean. Per-class AP would make the Balance step's promise checkable per class."
  - "The co-occurrence rule (weighted loss over sampling when the rare class shares its pictures) is reasoned, not measured: on blood cells, one seed and 8 epochs could not separate the strategies (see Verified by training)."
  - "Merging or dropping a class is doc 83's class map, not a strategy here. The plan points to it when a class has fewer than 10 examples."
security_read_sites: []
sister_projects: []
---

# 86 — Imbalance Strategy

## Purpose

A model rewards itself for being right often. With one class 12× as common as another,
it can score well while mostly ignoring the rare class, and the rare one is often the one
that matters. This feature picks a remedy from the dataset's own numbers, says why, and
shows what it will do. Training then applies it.

## Strategies (`app/ml/training/imbalance.py`)

| Strategy | What happens | Suits |
|---|---|---|
| `none` | training exactly as before the option existed | classes within 3× of each other |
| `weighted-loss` | each class's loss terms are scaled by `sqrt(1/count)`, normalised to a mean of 1 and capped at 10 | whole-image labels, outlines, and boxes whose rare class shares pictures with common ones |
| `balanced-sampling` | repeat-factor sampling (LVIS, 2019): an image is visited `max over its classes of sqrt(f_max / f_c)` times per epoch, where `f` is the share of images holding the class; the fraction is stochastically rounded, seeded per epoch, shuffled, and capped at 10 | boxes whose rare class lives in its own pictures |

- **Counts are objects, not images**, over the training indices only. That is what the
  loss adds up, and counting by image hides the imbalance (see *Found live*).
- **Detection weights scale only the positive terms of a class.** The background that
  every cell also votes on is untouched, which is what keeps a weight from being drowned
  in thousands of background cells.
- **Segmentation's background class** gets the weight of the most common class. It is
  never the rare one.
- **Sampling needs the cache's alignment.** The cache skips unreadable images, so
  `precompute_cache` now reports which samples it kept, and the strategy reads the
  annotations of exactly those.

## The recommendation (`app/prep/balance_plan.py`)

`GET /datasets/{id}/balance?target=` returns the imbalance ratio (objects), a
recommendation with a plain reason, the three options explained, and per class:
examples, images, the weight it would get and its average visits per epoch. Both are
computed by the training functions themselves. Rules:

1. A ratio of 3 or less → `none`.
2. Boxes, and the rarest class's images would be visited at least 1.5× → `balanced-sampling`.
3. Boxes, but the rare class shares its pictures with common ones (visits < 1.5×) →
   `weighted-loss`, with the reason spelled out.
4. Anything else → `weighted-loss`.

- **Fewer than 10 examples:** a warning that no setting can invent the missing variety.
  Add examples, or merge or drop the class in the Fix step.
- **Fine-tune targets:** `applies_to_training` is false until doc 90.

## Found live (2026-09-29)

**Blood cells, first version.** The planner recommended sampling, and showed weights of
1.2 / 0.91 / 0.9 for a 12× imbalance.
- **Cause:** both counted images. Platelets are in 201 of 364 pictures, always beside
  red cells, so by image they looked almost as common as red cells, while by object they
  number 361 against 4,153.
- **Why sampling could not help:** it would have shown platelet pictures 1.33× as often,
  and the red cells in them just as often.
- **Fix:** weights now count objects. Sampling is recommended only when it shifts the
  balance, and otherwise the reason explains the choice. The recommendation is now
  weighted loss, with platelets 1.32, red cells 0.39 and white cells 1.30.
- **Test:** the shape is pinned with the blood-cell proportions.

## Verified by training (Blood cells, DINOv2-small detection head, 8 epochs)

| Strategy | Best mAP | mAP50 by epoch | Time |
|---|---|---|---|
| none | 0.486 | 0.62 0.64 0.66 0.67 0.66 0.69 0.69 0.71 | 151 s |
| weighted-loss (recommended) | 0.494 | 0.65 0.68 0.67 0.71 0.70 0.70 0.71 0.71 | 151 s |
| balanced-sampling | 0.509 | 0.61 0.63 0.69 0.62 0.72 0.74 0.72 0.63 | 161 s |

**What this does and does not show.**
- **Both strategies run end to end** through the real runner and cache, and change
  training: the losses and curves differ.
- **Weighted loss learns faster early:** mAP50 0.65 after one epoch against 0.62.
- **No winner can be named.** With one seed and 8 epochs, the gaps (0.008 and 0.023
  mAP) are smaller than balanced sampling's own swing between epochs (±0.1). The
  recommendation rule for this case (weighting over sampling when the rare class shares
  its pictures) is therefore **not validated** by this run, and not refuted.
- Settling it needs several seeds and per-class AP (known issues).

## Bugs

(none yet — populated by /mdd bug when issues are reported)

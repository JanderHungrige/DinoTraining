---
id: 87-augmentation-presets
title: Augmentation Presets — Changed Copies That Never Leave Their Targets Behind
edition: DinoTraining
depends_on: [10-preprocessing-pipeline, 11-training-job, 85-model-input-planning]
relates: [11-training-job, 55-backbone-unfreezing, 86-imbalance-strategy, 88-preparation-recipe, 89-guided-preparation-flow, 90-training-consumes-recipe]
source_files:
  - backend/app/ml/augment.py
  - backend/app/ml/training/augmented.py
  - backend/app/ml/training/preparation.py
  - backend/app/ml/training/runner.py
  - backend/app/ml/training/live_loop.py
  - backend/app/ml/training/loop.py
  - backend/app/ml/training/config.py
  - backend/app/ml/training/job.py
  - backend/app/api/v1/training.py
  - backend/app/prep/augment_plan.py
  - backend/app/prep/input_preview.py
  - backend/app/api/v1/prep_augment.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/datasets/{dataset_id}/augmentation
  - POST /api/v1/datasets/{dataset_id}/augmentation-preview
  - POST /api/v1/training/jobs (new fields `augmentation`, `augment_copies`; job `notes`)
models: []
test_files:
  - backend/tests/test_augment.py
  - backend/tests/test_prep_augment_api.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, augmentation, presets, geometry, feature-cache, non-experts]
path: Prepare Data/Augment
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts:
  - function: "fine-tuning (RF-DETR, SAM) applies the recipe's augmentation preset"
    when: "a recipe for a fine-tune target carries one"
    satisfied_by: 90-training-consumes-recipe
satisfies_contracts: []
known_issues:
  - "The `augment` flag did nothing before this doc: the cache gate ignored it and no transform existed. It now means the `general` preset. Runs saved with `augment: true` before 2026-09-30 were not augmented."
  - "The preview draws boxes, not outlines. Masks are moved by the same `augment` call in training (tested), but the preview does not show them yet."
  - "The domain recommendation is a guess from class names, and it says so. The preview is what settles it."
  - "Fine-tuning (RF-DETR, SAM) does not augment yet; `applies_to_training` says so. Doc 90."
security_read_sites:
  - backend/app/prep/augment_plan.py:preview_augmentation (opens one sampled image of the dataset)
sister_projects: []
---

# 87 — Augmentation Presets

## Purpose

A model shown the same few hundred pictures every round learns those pictures. Showing
each one slightly changed (brighter, blurred, mirrored, cropped) teaches it what stays
the same, which is the object. For someone without experience the risks are invisible:
- a flip that leaves the boxes where they were teaches the wrong place;
- a mirrored "left arrow" teaches the wrong class.

This feature offers presets by kind of picture, shows them on the user's own data, and
makes both risks impossible.

## Rules

1. **Targets move with the picture.** One `augment` call moves the image, the boxes, the
   ignore regions, the masks and the ignore masks. A property test checks every preset
   across 12 seeds: each box lands exactly on its object's pixels, and each mask on the
   same pixels.
2. **A crop never cuts an object.** A crop that would is not taken (10 tries, then no
   crop).
3. **Nothing that changes meaning.**
   - The outdoor and documents presets carry no flips.
   - Any preset drops flips and turns when a class name contains a side, text or sign
     word (`MEANING_WORDS`: sign, text, arrow, left, right, signal, …).
   - The run records the classes that triggered it in the job's `notes`.
4. **Validation and test are never augmented.** A score on changed pictures would
   measure the changes.

## Presets

| Preset | Flips / turns | Crop (smallest side) | Colour | Blur | Grain |
|---|---|---|---|---|---|
| none | — | — | — | — | — |
| general | left-right | 0.8 | ±20 % | 10 % | — |
| outdoor (road, rail) | none (traffic has a side) | 0.85 | ±35 % | 30 % | 2 % |
| indoor (products) | left-right | 0.8 | ±25 % | 10 % | — |
| microscopy (top-down) | all flips, quarter turns | — | ±15 % | 20 % | — |
| documents | none | 0.9 | ±15 % | 20 % | 2 % |

`GET /datasets/{id}/augmentation?target=` recommends one from the class names (a
guess, and the reason says so) and marks which presets the meaning guard changes.
`POST …/augmentation-preview {target, preset, count}` shows one of the dataset's own
pictures:
- as the model gets it (doc 85's fit),
- then `count` changed versions,
- each with its boxes moved by the code training uses.

## In training

- **Feature cache (frozen backbone).** `augment_copies` changed copies (default 2) of
  every **training** image are cached next to the originals. Each round shows each
  training image as the original or one of its copies, at random (seeded).
  - The copies are capped to a 3 GB cache budget. The job's `notes` say when they are.
  - A DINOv2-small map at 448 px is about 1.5 MB.
- **Live pass (unfrozen backbone, doc 55).** Each training image is changed as it
  loads.
- **Stacking with doc 86:** balanced sampling decides *which* images a round visits;
  augmentation decides *which version* each visit shows.

## Verified live

**Previews (2026-09-30), checked by eye:**
- **Blood cells (microscopy):** one version mirrored and one turned a quarter, with every
  cell's box following it.
- **OSDaR (outdoor):** cropped and relit, never mirrored, boxes on the signals.
- Each preview took 0.0–0.1 s.

**Training, Blood cells, DINOv2-small detection head, 8 epochs, weighted loss:**

| Augmentation | Best mAP | mAP50 by epoch | Time |
|---|---|---|---|
| none | 0.494 | 0.65 0.68 0.67 0.71 0.70 0.70 0.71 0.71 | 151 s |
| microscopy, 2 copies | 0.498 | 0.64 0.66 0.70 0.67 0.69 0.72 0.71 **0.73** | 307 s |

- The cache is built for 364 originals plus 2 × ~255 training copies, which is why the
  run takes twice as long.
- The augmented run is still rising at epoch 8. Augmentation typically pays off over
  more rounds, and 8 cannot show the end state. One seed: a trend, not a result.
- The job's `notes` were empty, as they should be: no class was guarded, and every copy
  fit in memory.

**Found live: "platelets" switched mirroring off.** The meaning guard matched "plate" (as
in licence plate) inside the class name, so the microscopy preview showed colour changes
only.
- **Fix:** the guard now compares whole words, with the plural stripped.
- **Still guarded:** "stop sign", "left arrow" and "signal_pole".
- **Test:** pins the case.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

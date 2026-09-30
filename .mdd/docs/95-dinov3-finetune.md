---
id: 95-dinov3-finetune
title: DINO Backbone Fine-Tuning — A Backbone Variant With Its Own Head
edition: DinoTraining
depends_on: [55-backbone-unfreezing, 92-data-requirements-contract, 93-finetune-framework]
relates: [12-head-instance-registry, 24-dinov3-backbones, 97-finetune-ui]
source_files:
  - backend/app/finetune/adapters/backbone.py
  - backend/app/finetune/adapters/__init__.py
  - backend/app/finetune/requirements.py
  - backend/app/finetune/runner.py
  - backend/app/ml/foundation/variant.py
  - backend/app/ml/foundation/registry.py
  - backend/app/ml/foundation/build.py
  - backend/app/ml/foundation/run.py
  - backend/app/api/v1/foundation.py
routes:
  - POST /api/v1/finetune/jobs (finetune_id dinov2-small-*, dinov3-vitb16-*, dinov3-vitl16-*)
  - POST /api/v1/foundation/predict (a variant predicts as segmentation or classification)
models:
  - FoundationInstance weights_kind "backbone-variant" (backbone/ + head.pt)
test_files:
  - backend/tests/test_finetune_variants.py
  - backend/tests/test_finetune_runner.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [fine-tuning, dinov3, dinov2, unfreezing, backbone-variant, segmentation, classification]
path: Training/Fine-tuning/DINO backbones
initiative: dinotraining
wave: dinotraining-wave-12
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "DINOv3 itself was not run here: it is gated and not downloaded on this machine, and downloading it needs Jan's go-ahead. The adapter is the same code path (verified with DINOv2-small); the first DINOv3 run should be recorded here."
  - "A variant is offered as a foundation model with its own head. Training *further* heads on a variant (the head path keyed by the variant's id) is not offered yet."
  - "Snapshots copy the whole backbone state per improving epoch; for ViT-L that is ~1.2 GB of RAM each."
  - "Licence: DINOv3's terms for saving and redistributing fine-tuned weights are still open (wave research item)."
security_read_sites: []
sister_projects: []
---

# 95 — DINO Backbone Fine-Tuning

## Purpose

Doc 55 showed that a head cannot carry a backbone: unfreezing inside a `HeadInstance`
scored 0.000 in a fresh process, because a head stores only its own weights. Fine-tuning a
DINO backbone therefore lives on a path that saves the **whole model**. The last N blocks
train together with a classification or segmentation head, and the pair is saved as a
**backbone variant** under its own id.

## How (`adapters/backbone.py`)

- **A private copy of the backbone** (`fresh_backbone`), never the shared cache that every
  head in the app runs on.
- **Unfreezing and optimiser:** `apply_unfreeze(backbone, N)` (default 4) and
  `optimiser_for` (the backbone at 0.1× the head's rate), both doc 55's.
- **One loop:** training and evaluation go through the **live pass**
  (`run_live_epoch`, `evaluate_live`), so there is one definition of how a picture becomes
  features, targets and a loss.
- **A fair baseline** (the runner's new `baseline` hook): the same head, trained the same
  epochs on the **frozen** backbone. That is what the Training tab's head path would give
  the user, and what the variant has to beat. The runner also notes when a fine-tune ends
  up below its baseline.
- **Saved** as `backbone/` (`save_pretrained`) plus `head.pt`.

## Using the result (`foundation/variant.py`)

`BackboneVariantModel` loads the pair and predicts through the head machinery:
- plan, geometry, extract, head, decode, `build_payload`;
- listed in `GET /foundation` as a segmentation (masks) or classification (labels) model
  under its own id.

A head trained on the base can never run on the variant, nor the reverse: they are never
offered together.

## Models

- `dinov2-small-{classification,segmentation}`: installed and ungated, used for the live
  check;
- `dinov3-vitb16-*` and `dinov3-vitl16-*`: gated, same adapter.

## Verified live (2026-09-30)

DINOv2-small, segmentation, filled-ring convention set (recipe split 49/13/8), 4 epochs,
4 blocks unfrozen, 90 s including the baseline:

| | test mIoU | pixel accuracy |
|---|---|---|
| head on the frozen backbone (baseline) | 0.849 | 0.991 |
| backbone variant (best epoch 3) | **0.869** | 0.993 |

Listed as "rings DINOv2 variant" (segmentation, masks). `POST /foundation/predict` with its
id returned a masks payload with classes background / blob / ring; the first call took
6.4 s including the load.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

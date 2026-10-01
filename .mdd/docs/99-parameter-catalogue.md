---
id: 99-parameter-catalogue
title: Parameter Catalogue — Every Training Knob a Model Honours, Named and Explained Once
edition: DinoTraining
depends_on: [11-training-job-runner, 93-finetune-framework]
relates: [100-parameter-form, 102-training-knobs-for-agents, 94-sam2-finetune, 96-sam3-finetune, 95-dinov3-finetune]
source_files:
  - backend/app/params/__init__.py
  - backend/app/params/spec.py
  - backend/app/params/heads.py
  - backend/app/params/finetune.py
  - backend/app/params/sam.py
  - backend/app/api/v1/training_parameters.py
  - backend/app/api/v1/router.py
  - backend/app/api/v1/training.py
  - backend/app/api/v1/finetune_jobs.py
  - backend/app/ml/training/config.py
  - backend/app/ml/training/schedule.py
  - backend/app/ml/training/loop.py
  - backend/app/ml/training/live_loop.py
  - backend/app/ml/training/runner.py
  - backend/app/finetune/adapters/rfdetr.py
  - backend/app/finetune/adapters/sam2.py
  - backend/app/finetune/adapters/sam3.py
  - backend/app/finetune/adapters/sam3_loss.py
  - backend/app/finetune/adapters/backbone.py
  - backend/app/finetune/adapter.py
  - backend/app/finetune/runner.py
  - backend/app/ml/foundation/instances.py
routes:
  - GET /api/v1/training/parameters
  - GET /api/v1/training/parameters/{model_id}
models: []
test_files:
  - backend/tests/test_parameter_catalogue.py
  - backend/tests/test_training_schedule.py
  - backend/tests/test_finetune_sam2.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [training, fine-tuning, parameters, hyperparameters, defaults, non-experts, validation]
path: Training/Parameters
initiative: dinotraining
wave: dinotraining-wave-13
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "`save_best_only` is accepted by the head API for compatibility but has never been honoured: the best round is always kept. It is not in the catalogue, because a displayed knob that does nothing is worse than none."
security_read_sites: []
sister_projects: []
---

# 99 — Parameter Catalogue

## Purpose

Jan (2026-09-30): *"There are lots of parameters you can set for fine-tuning or training. We
only have epochs. Give all options for each model, like Rounds, with a name and the
technical term in brackets. Behind each a question mark with a short explanation and a good
default."*

This doc is the backend half: **one declaration per model family** of every parameter the
training code actually honours. That one declaration is read three ways:
- the form renders it (doc 100);
- the API validates against it;
- MCP returns it (doc 102).

The explanation is written once.

## Found while building: two knobs that were never knobs

- **Batch size:** the head API accepted `batch_size=16`, and the loop has always made one
  optimiser step per picture.
- **Save best only:** `save_best_only=False` changed nothing, because the best round is
  always kept.

**Decisions:**
- **Batch size is implemented honestly** as *pictures per step* (gradient accumulation), with
  the default changed to **1**. That is exactly what every run so far did, so no result
  moves.
- **`save_best_only` is left out of the catalogue.** It stays accepted, for compatibility.

## Architecture

- **`params/spec.py`** holds `Parameter` with these fields:
  - `key`, plain `label`, technical `term`, `help` (1–2 sentences), `default`, `why` (the
    default's reason);
  - `kind`: int, float, bool or choice;
  - range or `choices`;
  - `level` (basic or advanced), and `recipe_overrides` (the recipe's value wins when one
    is chosen).

  `ParameterSet` is one family's list. Its functions:
  - `resolve(values)`: fills defaults and refuses unknown keys, wrong types and
    out-of-range values, with a `ValueError` naming the parameter and its range;
  - `value(options, key)`: an adapter's lookup with the catalogue default.
- **`params/heads.py`** declares the DINO head family. **`params/finetune.py`** declares
  RF-DETR, SAM 2.1, SAM 3 and the DINO backbones.
- **`family_for(model_id)`** maps an id to its family. `head` is the head family. A
  fine-tune id is matched like `get_adapter`: `rf-detr-*`, `sam2*`, `sam3`, and
  `dinov2-*`/`dinov3-*-{classification,segmentation}`.

## The catalogue

| Family | Basic | Advanced |
|---|---|---|
| DINO head | Rounds (epochs) 20 · Learning speed (learning rate) 1e-3 · Pictures per step (batch size) 1 · Patience (early stopping) 5 | Weight shrinkage (weight decay) 0.01 · Speed schedule (learning-rate schedule) constant · Warm-up rounds (warm-up) 0 · Random seed (seed) 42 · Validation share (validation fraction) 0.2 · Test share (test fraction) 0.1 |
| RF-DETR | Rounds 10 · Learning speed 1e-4 · Pictures per step (gradient accumulation) 1 | Weight shrinkage 1e-4 · Gradient limit (gradient clipping) 0.1 · Backbone blocks to train (unfreeze) 0 · Random seed 42 |
| SAM 2.1 | Rounds 6 · Learning speed 1e-4 | Weight shrinkage 1e-4 · Loss weights: pixel focus (focal) 20, overlap (dice) 1, self-rating (IoU head) 1 · Box looseness (box jitter) 0.1 · Objects per step 16 · Memory for cached pictures (cache share) 0.15 · Random seed 42 |
| SAM 3 | Rounds 4 · Learning speed 1e-4 | Weight shrinkage 1e-4 · Loss weights: found or not (classification) 2, box position (L1) 5, box overlap (GIoU) 2, pixel focus (mask focal) 5, overlap (dice) 5 · Evaluation score threshold 0.5 · Memory for cached pictures 0.08 · Random seed 42 |
| DINO backbone | Rounds 6 · Learning speed 1e-3 · Backbone blocks to train (unfreeze) 4 | Backbone speed factor (backbone learning-rate scale) 0.1 · Weight shrinkage 0.01 · Random seed 42 |

**Every value above is today's behaviour, moved from a constant into a setting.** No
default changes a result. The two new knobs keep that property: the schedule's default is
*constant* and warm-up's is 0.

## Business Rules

1. **Only honoured parameters are declared.** A test sets each non-default value and
   checks that it reaches the training code.
2. **Defaults are the running code's defaults.** A drift test compares the head family
   with `TrainingConfig` and `TrainingRequest`.
3. **Unknown keys are refused, not ignored.** Before this, `options={"unfreez_blocks": 2}`
   trained silently with the default.
4. **A validation failure is a 422 naming the parameter** and its allowed range, never a
   500.
5. **The fine-tune API's `epochs` and `learning_rate` default per family.** SAM 3 takes 4
   rounds and a backbone 1e-3, instead of one number for all.
6. **The schedule is set per round, not per step.** Round *r* of *N* with *w* warm-up rounds
   runs at `lr × r/w` while `r ≤ w`. After that it runs at `lr` (*constant*), or at
   `lr × (0.05 + 0.95 × ½(1 + cos(π·t)))` with t = (r − w − 1) / (N − w − 1) (*cosine*: full speed on the first round after
   warm-up, ending at 5 %
   of the rate). Every parameter group scales by the same factor, so the backbone keeps its
   lower share.

## API

- `GET /api/v1/training/parameters` lists the families and the ids each covers.
- `GET /api/v1/training/parameters/{model_id}` returns the family's parameters with every
  field above. It gives a 404 for an unknown id.

## Data Flow

```
Form / MCP ──► POST /training/jobs or /finetune/jobs
                 └─ catalogue.resolve(values) ── ValueError → 422 (named parameter)
                       └─ TrainingConfig / FinetuneSettings.options (complete)
                             └─ adapter: value(options, key) → the running code
```

## Verified (2026-09-30)

- **Tests:** backend 1704 green; ruff and `mypy app` are clean.
- **Live backend:**
  - `GET /training/parameters/sam3` lists all eleven SAM 3 parameters with their terms and
    defaults.
  - An unknown id gives a 404.
  - `box_jitter: 0.9` gives a 422 with *"Box looseness (box jitter) must be between 0 and
    0.5, got 0.9"*.
- **A real head run** (DINOv2-small, 3 rounds, cosine, 1 warm-up round, 4 pictures per step)
  completed with falling loss. Its test head was deleted afterwards.
- **Provenance:** a fine-tuned model's `instance.json` now records every parameter
  (`parameters`), defaults included.

## Known Issues

See frontmatter.

## Bugs

(none yet)

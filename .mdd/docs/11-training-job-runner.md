---
id: 11-training-job-runner
title: Training Job Runner — Pluggable Execution, Task-Generic Loop
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: active
depends_on: [03-dataset-store, 07-backbone-feature-extractor, 08-head-registry, 09-head-implementations, 10-preprocessing-pipeline]
relates: [12-head-instance-registry, 13-training-metrics-stream]
source_files:
  - backend/app/ml/training/__init__.py
  - backend/app/ml/training/config.py
  - backend/app/ml/training/samples.py
  - backend/app/ml/training/losses.py
  - backend/app/ml/training/metrics.py
  - backend/app/ml/training/decode.py
  - backend/app/ml/training/job.py
  - backend/app/ml/training/loop.py
  - backend/app/ml/training/runner.py
test_files:
  - backend/tests/test_training_config.py
  - backend/tests/test_training_samples.py
  - backend/tests/test_training_losses.py
  - backend/tests/test_training_metrics.py
  - backend/tests/test_training_decode.py
  - backend/tests/test_training_runner.py
routes: []
models: []
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [training, job-runner, losses, metrics, early-stopping, feature-cache, splits]
path: Training/Runner
integration_contracts:
  - function: JobRunner protocol
    when: any code that starts, polls or cancels training
    why: Wave 6 swaps in a hyperscaler runner; callers must never touch LocalJobRunner directly
  - function: loss_for(spec) / metrics_for(spec) / decode_for(spec)
    when: computing loss, metrics, or decoding raw head output
    why: all three are keyed by head type, so the loop never branches on task
satisfies_contracts:
  - from: 08-head-registry
    function: get_head_type(head_type_id)
    when: resolving the configured head type before building anything
    status: done
    verified_at: "backend/app/ml/training/runner.py:48"
  - from: 10-preprocessing-pipeline
    function: plan_preprocessing(capabilities, spec)
    when: preparing every training and validation image
    status: done
    verified_at: "backend/app/ml/training/runner.py:93"
  - from: 09-head-implementations
    function: build_head(head_type_id, capabilities, num_classes)
    when: constructing the head to train
    status: done
    verified_at: "backend/app/ml/training/runner.py:105"
security_read_sites: []
known_issues:
  - "Detection map_75 is unstable across epochs on small datasets (observed 0.247 → 0.003 → 0.280 → 0.012 over 6 epochs while map_50 rose steadily to 0.954). Localisation is coarse because the head regresses ltrb from a 32x32 patch grid with an L1 loss; tight-IoU quality lags classification quality. Not a correctness bug — best-model selection uses `map`, the mean of both, so it does not chase the noise. Revisit with IoU/GIoU loss if detection quality matters in Wave 3."
  - "Classification labels are derived from single-class images only; images whose positive boxes name several classes are skipped and counted in `job.skipped_mixed_class_images`. Multi-label classification is out of scope for this wave."
sister_projects: []
---

# 11 — Training Job Runner

## Purpose

Trains a head against a frozen backbone: reads Wave 1 datasets, derives targets,
runs the loop, tracks metrics, applies early stopping and keeps the best weights.
Execution is behind a **pluggable runner interface** so Wave 6 can add a hyperscaler
runner without touching any caller.

## Architecture

```
TrainingConfig ─► JobRunner.submit() ─► TrainingJob (id, state, history)
                        │
                  LocalJobRunner (worker thread, like Wave 1's DownloadManager)
                        │
   samples.py ──► losses.py ──► metrics.py      all keyed by head type
                        │
                  best weights + final metrics ─► 12-head-instance-registry
```

**The loop never branches on task.** `loss_for(spec)` and `metrics_for(spec)` are
registries keyed by head-type id, exactly like `09`'s builders. Adding a head type
means adding a loss and a metric entry — never editing the loop.

### Frozen backbone ⇒ cache the features

Because the backbone never updates, a given image produces identical features every
epoch. When augmentation is off, the runner does **one** backbone pass over the dataset
and trains the head on cached features for all epochs. This turns a 20-epoch run from 20
backbone passes into 1 — the single biggest payoff of the frozen-backbone design.

With augmentation on, geometry changes per epoch, so features are recomputed. The cache
is therefore correctness-gated on `augment=False`, not a user setting.

## Data Model

### `TrainingConfig` (frozen) — good defaults, per the wave's demo-state

| Field | Default | Notes |
|---|---|---|
| `head_type_id`, `backbone_id`, `dataset_ids` | — | required |
| `epochs` | 20 | |
| `batch_size` | 16 | |
| `learning_rate` | 1e-3 | AdamW; a linear head on frozen features tolerates a high lr |
| `weight_decay` | 0.01 | |
| `val_fraction` / `test_fraction` | 0.2 / 0.1 | |
| `split_seed` | 42 | deterministic splits |
| `save_best_only` | True | |
| `early_stopping_patience` | 5 | epochs without primary-metric improvement |
| `augment` | False | off by default so the feature cache applies |

### `TrainingJob`
`job_id`, `state` (`pending`/`running`/`complete`/`failed`/`cancelled`), `epoch`,
`total_epochs`, `history: list[EpochRecord]`, `best_metric`, `best_epoch`, `message`.

`EpochRecord` carries `epoch`, `train_loss`, `val_loss` and a `metrics: dict[str, float]`
whose keys come from the head spec — **the stream in `13` must not hardcode metric names.**

## Business Rules

### Label derivation from Wave 1 data

Wave 1 stores boxes with `label ∈ {positive, negative, unclear}` and a `prompt`. That is
box-shaped data, so targets are derived:

- **Class vocabulary** = the sorted distinct `prompt` values of *positive* boxes. Sorted
  for determinism: a class order that shifts between runs makes saved weights
  uninterpretable.
- **`positive`** → training targets.
- **`negative`** → not a target. The user marked it *not an object*, so its region is
  legitimate background.
- **`unclear`** → neither target nor background. Cells covered by an unclear box are
  **ignored** in the loss. Forcing them to background trains the model to suppress
  exactly the cases the user could not decide.
- **Images with no positive boxes are kept** as pure-background samples for detection —
  they are real supervision.

### Classification labels are lossy — a documented limitation

Classification needs one label per image, and the store holds boxes. An image is used
when its positive boxes name exactly **one** class. Images mixing classes are **skipped
and counted**, and the count is surfaced on the job. Multi-label classification is not
in this wave; silently picking the first class would train a model on labels the user
never gave.

### Splits

Split by **image**, never by box. Boxes from one image landing in both train and val is
leakage that inflates validation metrics with no visible symptom. Deterministic in
`split_seed`.

### Best model and early stopping

Both read `spec.primary_metric` and `spec.primary_metric_mode` — `08` guarantees a
trainable head has them. Early stopping counts epochs without improvement on that same
metric, so "best" and "stop" can never disagree.

### Depth cannot be submitted

`linear-depth` has `trainable=False`; `submit` rejects it with a message pointing at the
pretrained default. This is the check that proves the registry's two-axis model is real.

## Data Flow

Reads `03-dataset-store.image_annotations`. Uses `07` for features, `10` for geometry and
target transforms, `09` for the head. Emits `TrainingJob` state consumed by `13` and best
weights consumed by `12`.

## Dependencies

`03-dataset-store`, `07-backbone-feature-extractor`, `08-head-registry`,
`09-head-implementations`, `10-preprocessing-pipeline`

## Security

No user-supplied paths: dataset ids resolve through the store, model ids through the
registry. Image paths come from the store's own rows, written by Wave 1's confined
`_store_image`.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

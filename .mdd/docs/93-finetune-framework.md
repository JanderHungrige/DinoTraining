---
id: 93-finetune-framework
title: Fine-Tune Framework — One Runner, Per-Model Adapters, Base vs Fine-Tuned Always
edition: DinoTraining
depends_on: [44-rfdetr-finetune, 90-training-consumes-recipe, 92-data-requirements-contract]
relates: [94-sam2-finetune, 95-dinov3-finetune, 96-sam3-finetune, 97-finetune-ui, 98-finetune-for-agents]
source_files:
  - backend/app/finetune/adapter.py
  - backend/app/finetune/data.py
  - backend/app/finetune/runner.py
  - backend/app/finetune/adapters/__init__.py
  - backend/app/finetune/adapters/rfdetr.py
  - backend/app/ml/foundation/instances.py
  - backend/app/api/v1/finetune_jobs.py
  - backend/app/api/v1/router.py
routes:
  - POST /api/v1/finetune/jobs
  - GET /api/v1/finetune/jobs
  - GET /api/v1/finetune/jobs/{job_id}
  - POST /api/v1/finetune/jobs/{job_id}/cancel
models:
  - FoundationInstance (+ finetune_id, recipe_id, baseline_metrics, weights_kind)
test_files:
  - backend/tests/test_finetune_runner.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [fine-tuning, runner, adapters, rf-detr, baseline, provenance, recipe]
path: Training/Fine-tuning/Framework
initiative: dinotraining
wave: dinotraining-wave-12
wave_status: complete
integration_contracts: []
satisfies_contracts:
  - from: 92-data-requirements-contract
    function: "a fine-tune job runs `preflight` and refuses with `refusal()` before starting"
    when: "any fine-tune is started"
    status: done
    verified_at: "backend/app/finetune/runner.py:FoundationFinetuneRunner.submit"
known_issues:
  - "Doc 44's RF-DETR runner and `/foundation/finetune` remain, because the Training tab's fine-tune panel uses them. Doc 97 moves the panel onto `/finetune/jobs`; until then RF-DETR can be fine-tuned both ways."
  - "The best epoch is kept in memory and saved once at the end; a cancelled run saves nothing (doc 44's runner saved on every improvement)."
  - "For a detector learning new classes the base score is ~0 by construction (its classifier is re-opened). The comparison says more for class-agnostic SAM (doc 94)."
security_read_sites: []
sister_projects: []
---

# 93 — Fine-Tune Framework

## Purpose

Doc 44 fine-tuned one model. Wave 12 fine-tunes four families, and they differ in only
four places:
- how a sample becomes a training step;
- how the model is scored;
- what is saved;
- how it is loaded.

Everything else is one lifecycle, written once. Every fine-tune also answers "did it
help?" with numbers: the base model and the fine-tuned model are scored on the same
held-out pictures.

## Shape

```
POST /finetune/jobs {finetune_id, dataset_ids, name, recipe_id?, epochs, learning_rate, options}
  preflight (doc 92) per dataset → 409 with the failed rules, nothing started
  load_data: build_samples (fixes applied) → the recipe's split, or seeded 80/20
  adapter.prepare → baseline = evaluate(held_out)
  epochs: train_epoch → evaluate(val) → keep the best snapshot
  restore(best) → final = evaluate(held_out) → save → FoundationInstance
```

- `held_out` is the test side, or validation when there is no test side. In that case the
  job notes that the gain is optimistic, because validation also picked the epoch.
- The instance records the fine-tune id, the recipe, the base score, the fine-tuned score
  and `weights_kind`: `full` (RF-DETR), `sam-mask-decoder` (doc 94) or `backbone-variant`
  (doc 95).

## Adapters (`adapter.py`)

`prepare`, `train_epoch`, `evaluate`, `snapshot`, `restore` and `save`, plus
`primary_metric` and `weights_kind`. `adapters/__init__.py` maps a fine-tune id to its
adapter, one line per family. **RF-DETR** is the first, built from doc 44's own pieces
(`prepared_model`, `freeze_backbone`, `to_detr_labels`, `evaluate`).

## Verified live (2026-09-30)

**RF-DETR nano on Blood cells, recipe "blood v1"** (stored split, 253/75/36), 2 epochs,
261 s:

| | test mAP | mAP50 | mAP75 |
|---|---|---|---|
| base (classifier re-opened for the 3 classes) | 0.000 | 0.000 | 0.000 |
| fine-tuned (best epoch 2; val 0.637) | **0.616** | 0.750 | 0.482 |

On the same test pictures, the DINOv2-small detection head from doc 90 scored **0.412**
after 8 epochs.

**Preflight on live data:**
- SAM 2 on Blood cells is refused, with the reasons: no masks and no recipe.
- RF-DETR with its recipe passes every check.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

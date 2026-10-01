---
id: 120-model-card
title: Model Card — Everything an Application Needs to Use a Trained Model, in One JSON
edition: DinoTraining
depends_on: [11-training-job-runner, 16-inference-engine, 90-training-consumes-recipe, 93-finetune-framework]
relates: [121-export-bundle, 122-onnx-export, 123-mlflow-tracking, 124-mlflow-backfill]
source_files:
  - backend/app/mlops/__init__.py
  - backend/app/mlops/card.py
  - backend/app/mlops/card_parts.py
  - backend/app/api/v1/model_cards.py
  - backend/app/api/v1/router.py
  - backend/app/datasets/schema.py
  - backend/app/ml/heads/instances.py
  - backend/app/ml/heads/store.py
  - backend/app/ml/training/persist.py
  - backend/app/ml/foundation/instances.py
  - backend/app/finetune/runner.py
  - backend/app/mcp/model_tools.py
  - backend/app/mcp/server.py
routes:
  - GET /api/v1/cards/heads/{instance_id}
  - GET /api/v1/cards/finetuned/{instance_id}
models:
  - head_instances
test_files:
  - backend/tests/test_model_card.py
  - backend/tests/test_mcp_server.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mlops, model-card, export, provenance, heads, fine-tuning]
path: MLOps/ModelCard
initiative: dinotraining
wave: dinotraining-wave-15-6
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 120 — Model Card

## Purpose

- **Jan:** "what everything is needed to build it into an application".
- **The problem today:** a head is a few-KB `.safetensors` file. Its backbone, head type,
  class order and preprocessing live only in the app's SQLite. Handed over alone, it is
  unusable, and silently: a wrong class order or normalisation gives confident wrong
  answers.
- **The card** is one JSON, `model.json`, that says all of it. The export bundle (121),
  ONNX (122) and MLflow (123, 124) all carry the same card, so there is one description of
  a model, not three.

## Schema `dinotraining.model-card/1`

| Field | For a head | For a fine-tuned model |
|---|---|---|
| `schema` | `dinotraining.model-card/1` | same |
| `model` | id, name, `kind: head`, `origin` (trained-here / pretrained-default / community), created, app version | id, name, `kind: finetuned`, `finetune_id`, created, app version |
| `task` | classification / detection / segmentation / depth | segmentation (SAM), detection (RF-DETR), … |
| `base` | the backbone: id, HuggingFace repo, family, `patch_size`, `embed_dim`, `num_prefix_tokens`, licence, non-commercial | the base model: id, repo, licence, non-commercial |
| `head` | type id and title, what it consumes (CLS and/or patch grid), module class, `num_classes` | — (`weights_kind` instead: full, `sam-mask-decoder`, …) |
| `classes` | in order; index *i* in the outputs is `classes[i]` | same |
| `preprocessing` | `geometry` (`aspect-preserve`: letterbox, pad 0, centred / `center-crop`), `size`, bilinear resampling, RGB/255, `mean`, `std`, layout `(B,3,H,W) float32` | the base model's own processor (named) |
| `features` | `last_hidden_state`; the first `num_prefix_tokens` tokens are CLS (+ registers); the rest reshape to `(B, embed_dim, H/p, W/p)` | — |
| `outputs` | per task: which tensors, and how the app decodes them (e.g. detection: per-patch class logits and left/top/right/bottom distances in patch units; overlap suppression) | per weights kind |
| `metrics` | the best epoch's validation metrics and the `test_*` ones; `primary_metric` | metrics and `baseline_metrics` (the base model on the same pictures) |
| `training` | epochs, best epoch, datasets (id and name), recipe (id and name, if one was used), the settings snapshot, `history` per epoch (when recorded) | same, with `parameters` |
| `weights` | file names, format, SHA-256 | same |

- **Licences are carried through.** A head on DINOv3 inherits DINOv3's terms; the card says
  so in `base.licence` and `base.non_commercial`.

## Per-epoch history, from now on

- **Today:** it lives only in memory while a job runs.
- **From now on:**
  - heads store it in a new nullable column `head_instances.history` (JSON, added in
    place by the migration runner);
  - fine-tuned models store it in `instance.json` as `history`.
- **Older models** say `"history": null`, with `"history_note": "not recorded (trained
  before Wave 15.6)"`.

## API and MCP

- `GET /api/v1/cards/heads/{id}` and `GET /api/v1/cards/finetuned/{id}` return the card, or
  404 with the reason.
- MCP `get_model_card(kind, id)`: an agent integrating a model reads the same contract.

## Rules

1. **The card is built from the stored record, never typed by hand.** Preprocessing comes
   from `plan_preprocessing(backbone, head spec)`, the function training and inference use.
   A card that disagreed with the app would be worse than none.
2. **The class order is the stored order.** A test pins that index *i* of a trained head's
   output is `classes[i]`.
3. **No secret or local user path is in the card** beyond the weight file names.

## Verified (2026-09-30)

- **Tests:** `test_model_card.py` (6).
  - A head's card has the stored class order, the catalogue base, the head type and the
    decode text.
  - Weights carry a SHA-256, and the card has no local folder.
  - History is present for new heads, and absent with a note for older ones.
  - A backbone that is not installed still gives a card.
  - A fine-tuned card has its base, weights kind, baseline and history.
  - Backend: 1851 green; ruff and mypy (234 files) clean.
- **Live, on the real library (restarted backend; the `history` column was added in place
  to the existing database):**
  - The head "Object detection: person +2 more" gave:
    - base facebook/dinov2-small (patch 14, embed 384, 1 prefix token, Apache-2.0);
    - DetectionHead;
    - classes person, signal, signal_pole;
    - letterbox 448, ImageNet mean and std;
    - its weights' SHA-256;
    - "history not recorded (trained before Wave 15.6)".
  - The fine-tuned SAM 2.1 model gave its base, `mask_decoder.pt` with SHA-256, and miou
    0.936 against baseline 0.957.
- **Found live:** the SAM card said "backbone not installed here". SAM is not a backbone
  at all, so structure is now read only for backbones. A test pins it.

## Bugs

(none yet)

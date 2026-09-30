---
id: 92-data-requirements-contract
title: Data Requirements Contract — What Each Fine-Tunable Model Needs, Checked Before Training
edition: DinoTraining
depends_on: [44-rfdetr-finetune, 81-dataset-audit, 88-preparation-recipe]
relates: [93-finetune-framework, 94-sam2-finetune, 95-dinov3-finetune, 96-sam3-finetune, 97-finetune-ui, 98-finetune-for-agents]
source_files:
  - backend/app/finetune/__init__.py
  - backend/app/finetune/requirements.py
  - backend/app/finetune/preflight.py
  - backend/app/api/v1/finetune_requirements.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/finetune/requirements
  - GET /api/v1/finetune/requirements/{finetune_id}
  - POST /api/v1/finetune/check
models: []
test_files:
  - backend/tests/test_finetune_requirements.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [fine-tuning, requirements, preflight, sam2, sam3, dinov3, rf-detr, non-experts, mcp]
path: Training/Fine-tuning/Requirements
initiative: dinotraining
wave: dinotraining-wave-12
wave_status: complete
integration_contracts:
  - function: "a fine-tune job runs `preflight` and refuses with `refusal()` before starting"
    when: "any fine-tune is started"
    satisfied_by: 93-finetune-framework
satisfies_contracts: []
known_issues:
  - "The minimums are floors chosen from what each model starts with, stated with their reason. They are not measured thresholds; doc 94 onwards should report whether they held."
  - "The memory figure for SAM 3 is an estimate; doc 96 measures it."
security_read_sites: []
sister_projects: []
---

# 92 — Data Requirements Contract

## Purpose

Jan's request for Wave 12: *what matters most is telling the user and the assistant exactly
what form the training data has to take for each model.* This is the one source for that.
It is rendered three ways:
- the Training tab's requirements card (doc 97);
- the API and MCP answer (doc 98);
- a **preflight** that refuses before a job starts, naming the rule, the numbers and the
  fix.

## The contract (`requirements.py`)

Per fine-tunable model (`id`):

| Field | Meaning |
|---|---|
| `task`, `annotation_kind`, `prompt_kind` | e.g. SAM 2: segmentation, instance masks, prompts made from each mask's box |
| `min_images`, `min_instances_per_class`, `minimums_why` | floors, and why |
| `image_sizes` | how the model resizes, and what that costs |
| `recipe_required` | a Wave 11 recipe must be given: its leak-free split is where base vs fine-tuned is compared |
| `gates` | HuggingFace gating, licence approval, memory |
| `data_format` | **what the training data must look like**, as a paragraph a person or an assistant can act on |
| `what_trains` | what changes and what stays frozen |
| `available`, `unavailable_reason` | false until the model's adapter lands (docs 94–96) |

**Models:**
- RF-DETR (nano), trainable since doc 44;
- SAM 2.1 (small);
- SAM 3;
- DINOv3 ViT-B/16 and ViT-L/16, each for classification and for segmentation.

## Preflight (`preflight.py`)

`POST /finetune/check {finetune_id, dataset_id, recipe_id?}` returns `Readiness` with one
check per rule:
- the adapter is available;
- the model is installed (the fix names Admin, and the token for gated models);
- the dataset has the right annotation kind (the fix *is* the data format);
- enough images;
- enough instances per class (the thin classes are named);
- a recipe that is up to date, when one is required.

The dataset is read as training reads it: exclusions and the class map applied (doc 83).
`refusal()` joins the failed checks into one message for a 409 or an MCP error.

## Verified

Tests over the real app:
- a box dataset against SAM 2 fails on annotation kind (the fix is the mask data format),
  on the missing recipe, and on the install;
- the same boxes against RF-DETR pass everything except the install;
- thin classes are named.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

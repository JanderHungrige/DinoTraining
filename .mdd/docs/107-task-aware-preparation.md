---
id: 107-task-aware-preparation
title: Task-Aware Preparation — Checks for Labels, Outlines and SAM 3 Phrases; Steps a Model Does Not Use
edition: DinoTraining
depends_on: [81-dataset-audit, 89-guided-preparation-flow, 103-phrase-data-model, 101-default-recipes]
relates: [104-annotation-target, 108-prompts-and-hard-negatives]
source_files:
  - backend/app/prep/task_facts.py
  - backend/app/prep/findings_task.py
  - backend/app/prep/finding_types.py
  - backend/app/prep/findings.py
  - backend/app/prep/audit.py
  - apps/frontend/src/components/prepare/PrepareSteps.tsx
  - apps/frontend/src/components/prepare/StepNav.tsx
routes: []
models: []
test_files:
  - backend/tests/test_prep_findings_task.py
  - apps/frontend/src/components/prepare/PrepareSteps.test.tsx
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, audit, sam3, masks, classification, phrases, non-experts]
path: Prepare data/Task-aware
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Holes in outlines are not flagged: whether a ring has one is a convention (doc 94's filled rings), not a mistake."
  - "An outline 'leaking outside its box' cannot happen here: a stored outline's box is derived from it (doc 22)."
security_read_sites: []
sister_projects: []
---

# 107 — Task-Aware Preparation

## Purpose

Jan (2026-09-30) asked:
- *"The checklist is great for classification. Is it also good for bounding boxes and
  segmentation?"*
- *"SAM 3 is missing"*, and does it need its own recognition in Prepare data?

**Before this doc:**
- The audit knew boxes and masks only as present or absent (`wrong-annotation-kind`).
- The size rules served detectors.
- SAM 3 had no profile until doc 101.

## New rules (`findings_task.py`), each with what, why and action

| Rule | Target | Finds | Severity |
|---|---|---|---|
| `mixed-classes` | labels (classifier) | Pictures whose annotations name two or more classes: a classifier skips them | warn |
| `fragmented-outlines` | masks | Outlines in several pieces of at least 20 px: right for an occluded object, wrong for specks | info |
| `duplicate-outlines` | masks | Two outlines on one picture with IoU ≥ 0.8: one object marked twice | warn |
| `thin-phrases` | SAM 3 | Phrases with fewer than 50 outlines (doc 92's minimum) | warn |
| `unchecked-pictures` | SAM 3 | Pictures not checked for every phrase; when *none* is, it says training falls back to "no outline = none here" | warn |
| `no-variations` | SAM 3 | Phrases with a single wording | info |
| `no-confirmed-negatives` | SAM 3 | Checks exist, but none says "not in this picture" | info |

**The facts** (`task_facts.py`) are collected only for targets that use them:
- **outline shapes** (a decode per outline, `scipy.ndimage.label` for pieces, IoU within
  overlapping boxes) for mask targets;
- **phrase checks** (doc 103's tables) for SAM 3.

A detector's audit costs what it did before.

## Steps a model does not use

- **The rule:** fine-tuning a whole model (RF-DETR, SAM 2, SAM 3) takes the recipe's split,
  class map and exclusions, but neither class balancing nor changed copies. Those two steps
  are marked **"(not used)"** in the step list for those targets.
- **Opening one** says why, and that the recipe still records the choice for a DINO head.
- **Head targets** are unchanged.

## Verified (2026-09-30)

- **Tests:** backend 1761 green (6 new); frontend 1026 green; ruff, mypy app and tsc are
  clean.
- **Live SAM 3 audit** of "Wave 12 filled-ring convention" found:
  - "Only 70 images";
  - "70 of 70 pictures not checked for every phrase", with the fallback explained;
  - "4 outline(s) in several pieces" of 200;
  - "2 phrase(s) without variations: blob, ring".

  There was no thin-phrase finding, correctly: 61 and 139 outlines.
- **Prepare data, dataset and "Fine-tune SAM 3":** steps 5 and 6 read "Unequal classes (not
  used)" and "Changed copies (not used)".

## Bugs

(none yet)

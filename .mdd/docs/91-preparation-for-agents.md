---
id: 91-preparation-for-agents
title: Preparation for Agents — MCP Tools and a "Prepare Before You Train" Guide
edition: DinoTraining
depends_on: [63-agent-guide, 64-mcp-server, 81-dataset-audit, 82-external-data-intake, 83-safe-fixes, 84-leakage-safe-split, 85-model-input-planning, 88-preparation-recipe, 90-training-consumes-recipe]
relates: [63-agent-guide, 64-mcp-server, 89-guided-preparation-flow]
source_files:
  - backend/app/mcp/prep_tools.py
  - backend/app/mcp/tools.py
  - backend/app/mcp/client.py
  - backend/app/mcp/server.py
  - backend/app/docs/workflows_prepare.py
  - backend/app/docs/workflows.py
routes:
  - /mcp (tools inspect_coco_export, import_coco_dataset, audit_dataset, fix_dataset, split_dataset, plan_preparation, save_recipe, list_recipes; get_job kind "audit"; recipe_id on train_head and finetune_model)
  - GET /api/v1/docs/agent-guide (section 2c)
models: []
test_files:
  - backend/tests/test_mcp_server.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mcp, agents, data-preparation, guide, recipe]
path: Connection/Prepare
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The 'what the model sees' preview is not a tool: its pictures are data URLs that would flood a model's context. `plan_preparation` gives the same numbers and the tiling decision; the pictures are for people, in the Prepare data tab."
  - "There is no one-call 'prepare with the recommendations'. An agent runs the steps, which is deliberate for the steps that need the user (class merges, judgement findings), and a convenience still missing for the rest."
security_read_sites: []
sister_projects: []
---

# 91 — Preparation for Agents

## Purpose

An assistant is most likely to do harm with preparation by being helpful:
- it splits video frames at random;
- it trains on objects two pixels wide;
- it merges classes it should have asked about.

The API has had every preparation step since docs 81–90. This makes them tools, whose
descriptions say what each step protects against, what to report, and when to ask the
user instead of deciding. It also gives the guide a "prepare before you train" recipe.

## Tools (`app/mcp/prep_tools.py`)

| Tool | Wraps | What its description insists on |
|---|---|---|
| `inspect_coco_export` | `POST /datasets/import/coco/inspect` | check before import; a null convention means ask; the 162-of-273 figure |
| `import_coco_dataset` | `POST /datasets/import/coco` | now takes `box_convention`, `class_map`, `keep_source_split` from the inspection (moved here from `tools.py`) |
| `audit_dataset` | `POST /datasets/{id}/audit` (a job, kind `audit`) | audit for the model you will train; report problems in their own words; judgement findings go to the user |
| `fix_dataset` | `POST /datasets/{id}/fixes` | safe fixes only; **ask before merging** classes; audit again after |
| `split_dataset` | `POST /datasets/{id}/split` | never split video at random (+42 % inflation); report the warnings |
| `plan_preparation` | input plan + balance + augmentation, in one call | say so when tiling is recommended |
| `save_recipe` | `POST /datasets/{id}/recipes` | recommendations when left out; a 409 names the missing step |
| `list_recipes` | `GET /datasets/{id}/recipes` | only an up-to-date recipe trains |

`train_head` and `finetune_model` take `recipe_id` and say what it changes.
`get_job` knows kind `audit`. The server's instructions name the preparation order before
anything else.

## The guide

The guide (doc 63) has a new section, **2c. Prepare the data before you train — do not
skip this**, between getting data in and training. It covers:
1. inspect an export before importing it;
2. audit;
3. fix what is safe, and ask about the rest;
4. split;
5. check the input plan;
6. save a recipe;
7. train with it and report `test_metrics`.

The worked example now prepares before it fine-tunes.

## Found while building it

**Every tool's error explanation was lost on the way to the model.**
- **Where:** `ApiError` was a `RuntimeError`. `mcp` 2.x passes the text of a
  `ToolError` through and replaces every other exception with "Error executing tool
  <name>".
- **Effect:** the carefully worded API refusals ("Run the Audit step first", "Model not
  installed …") reached the model as nothing. This affected the tools from doc 64 too.
- **Why the test missed it:** doc 64's failure test only checked `isError`.
- **Fix:** `ApiError` is now a `ToolError`.
- **Tests:** the failure test now also checks that the reason arrives, and a new test
  drives the preparation tools against the real app, refusal included.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

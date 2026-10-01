---
id: 102-training-knobs-for-agents
title: Training Knobs for Agents — The Same Parameters and Default Recipes over MCP
edition: DinoTraining
depends_on: [99-parameter-catalogue, 101-default-recipes, 64-mcp-server, 98-finetune-for-agents]
relates: [99-parameter-catalogue, 101-default-recipes, 63-agent-api-guide]
source_files:
  - backend/app/mcp/training_tools.py
  - backend/app/mcp/tools.py
  - backend/app/mcp/finetune_tools.py
  - backend/app/mcp/server.py
  - backend/app/docs/workflows_finetune.py
  - backend/app/docs/workflows_prepare.py
routes: []
models: []
test_files:
  - backend/tests/test_mcp_server.py
  - backend/tests/test_agent_docs.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mcp, agents, parameters, recipe, defaults, guide]
path: Connection/MCP/Training knobs
initiative: dinotraining
wave: dinotraining-wave-13
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 102 — Training Knobs for Agents

## Purpose

Wave 13's demo ends with an assistant asking for a model's parameters and making a default
recipe over MCP, and getting what the user sees. The rule since doc 98: **the user and the
assistant are told the same thing**.

## Tools

- **`get_training_parameters(model_id)`** takes `"head"` or a fine-tune id.
  - It returns doc 99's catalogue: label, term, help, default and why, range, and level.
  - The docstring says to use the defaults unless the user asks for something, and to
    report every non-default value it sends.
- **`create_default_recipe(dataset_id, model_id, head_type_id?, backbone_id?)`** starts
  doc 101's job and returns its id.
  - Poll it with `get_job` and kind `default-recipe` (a new kind).
  - The finished job carries `recipe.id` for `train_head` or `start_finetune`.
- **`train_head`:**
  - `epochs` and `learning_rate` are optional (the catalogue's defaults).
  - A new `parameters` dict carries any other head parameter: `batch_size`,
    `weight_decay`, `lr_schedule`, `warmup_epochs`, `early_stopping_patience`, and so on.
- **`start_finetune`:**
  - `epochs` and `learning_rate` default to the **model's own** catalogue values.
  - The hardcoded 1e-3 or 1e-4 in the tool is gone.
  - A new `options` dict carries any other parameter. `unfreeze_blocks` stays as a named
    argument, for doc 98's callers.

## Guide

- **Section 2c (recipes)** gains the shortcut: "no recipe yet → `create_default_recipe`".
- **Section 4 (fine-tuning)** gains a step 0: `GET /training/parameters/{finetune_id}`,
  with the rule to keep the defaults unless asked.
- The DINO-backbone line no longer says "use a learning rate of 0.001". The catalogue
  already defaults to it.

## Business Rules

1. **An unknown option is a tool error naming it** (the API's 422), never silently ignored.
2. **Docstrings name the kind for `get_job`,** as every job-starting tool does (doc 64's
   contract test).

## Verified (2026-09-30)

- **Tests:** backend 1725 green (MCP contract, the new tools against the real API, and the
  guide's content); ruff and mypy app are clean.
- **Live MCP (streamable HTTP on the running backend):**
  - `get_training_parameters("sam2.1-hiera-small")` returned "SAM 2.1": Rounds (epochs) 6,
    Learning speed (learning rate) 0.0001, Weight shrinkage 0.0001, Pixel focus (focal
    loss) 20, …
  - `create_default_recipe` on "Wave 11 intake check" for `rf-detr-nano`, polled with
    `get_job(kind="default-recipe")`, returned the recipe made from the UI minutes earlier:
    *"An up-to-date default recipe already exists"*, v1. The UI and the assistant land on
    the same recipe.

## Bugs

(none yet)

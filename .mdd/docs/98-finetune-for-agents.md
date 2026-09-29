---
id: 98-finetune-for-agents
title: Fine-Tuning for Agents — Requirements, Checks and Jobs Over MCP
edition: DinoTraining
depends_on: [64-mcp-server, 91-preparation-for-agents, 92-data-requirements-contract, 93-finetune-framework]
relates: [63-agent-guide, 97-finetune-ui]
source_files:
  - backend/app/mcp/finetune_tools.py
  - backend/app/mcp/tools.py
  - backend/app/mcp/prep_tools.py
  - backend/app/mcp/server.py
  - backend/app/docs/workflows_finetune.py
  - backend/app/docs/workflows.py
routes:
  - /mcp (get_finetune_requirements, check_dataset_for, start_finetune; get_job kind "foundation-finetune")
  - GET /api/v1/docs/agent-guide (section 4 rewritten)
models: []
test_files:
  - backend/tests/test_mcp_server.py
  - backend/tests/test_agent_docs.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [mcp, agents, fine-tuning, requirements, guide]
path: Connection/Fine-tuning
initiative: dinotraining
wave: dinotraining-wave-12
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "`finetune_model` (RF-DETR through doc 44's endpoint) is removed in favour of `start_finetune`. A client that cached the old tool list sees it disappear."
security_read_sites: []
sister_projects: []
---

# 98 — Fine-Tuning for Agents

## Purpose

The wave's demo-state ends with an assistant that asks for SAM 2's requirements and gets
the same card the user sees, and a fine-tune started over MCP with a dataset that breaks
a rule being refused with the same explanation. This is that.

## Tools (`app/mcp/finetune_tools.py`)

| Tool | Wraps | Its description insists on |
|---|---|---|
| `get_finetune_requirements` | `GET /finetune/requirements[/{id}]` | relay `data_format` as it is; the minimums have reasons |
| `check_dataset_for` | `POST /finetune/check` | relay failed rules with their fix; do not start until ready |
| `start_finetune` | `POST /finetune/jobs` | a job (kind `foundation-finetune`); report base **and** fine-tuned; "nothing saved" is a result |

- `finetune_model` is replaced by `start_finetune`, which covers every model, including
  RF-DETR.
- `train_head` now points at `start_finetune` for boxes, with the leak-free numbers.
- A refusal reaches the model with its reasons, because `ApiError` has been a `ToolError`
  since doc 91.

## The guide

Section 4 is rewritten for every model:
1. read the requirements and relay them;
2. check;
3. start and poll;
4. report both numbers.

It carries the measured cases:
- RF-DETR 0.62 against a head's 0.41;
- SAM 2 made worse on shapes it already did well (0.957 → 0.936);
- SAM 2 improved on a convention it could not know (0.804 → 0.957).

## Verified

Over the real JSON-RPC endpoint (test):
- `get_finetune_requirements("sam3")` returns the noun-phrase data format;
- `start_finetune` for SAM 2 on an empty dataset is an error whose text names the outline
  requirement and Prepare data.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

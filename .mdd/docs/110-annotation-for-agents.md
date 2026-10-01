---
id: 110-annotation-for-agents
title: Annotation for Agents — Targets, Phrases, Checks and the Guideline over MCP
edition: DinoTraining
depends_on: [103-phrase-data-model, 104-annotation-target, 108-prompts-and-hard-negatives, 109-annotation-quality-aids, 64-mcp-server, 63-agent-api-guide]
relates: [102-training-knobs-for-agents, 98-finetune-for-agents]
source_files:
  - backend/app/mcp/annotation_tools.py
  - backend/app/mcp/server.py
  - backend/app/docs/workflows_annotate.py
  - backend/app/docs/workflows.py
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
tags: [mcp, agents, phrases, sam3, guideline, hard-negatives]
path: Connection/MCP/Annotation
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Outline editing (doc 106) has no MCP tool of its own; the guide points at its REST routes (POST /segment/boxes, /segment/refine), which an assistant calls like any other."
security_read_sites: []
sister_projects: []
---

# 110 — Annotation for Agents

## Purpose

The rule since doc 98: the user and the assistant are told the same thing. Wave 14's demo
ends with *"an assistant adds a phrase with variations and sets picture statuses"*.

## Tools

**`get_annotation_targets()`**
- Returns doc 104's matrix, with every reason.
- The assistant recommends "keep all options open" when the user is unsure.

**`list_phrases(dataset_id)`**
- Returns doc 103's listing: variations, look-alikes, outlines per phrase, and checks.

**`add_phrase(dataset_id, text, class_name?)`**
- Comma-separated variations.
- The docstring says two to four are enough.
- Refusals name both phrases.

**`set_phrase_status(dataset_id, path, phrase, status)`**
- `complete`, `absent` or null.
- **The docstring carries the rules an assistant would otherwise break:**
  - only checked pictures teach;
  - a wrong *absent* teaches the model to miss the object;
  - pictures with a look-alike present are the best negatives.

**`get_annotation_guideline` / `set_annotation_guideline`**
- The assistant reads the guideline before annotating or judging annotations.
- It agrees any new text with the user before saving.

## Guide

- **New section 2d, "Annotate for the model you will train":** it sits before 2c (prepare),
  because annotation precedes preparation.
- **It covers:**
  - targets;
  - the guideline;
  - SAM 3's three layers per picture (outlines, phrases, checks), with the REST calls;
  - hard negatives, and that *unclear* is never a negative.
- **The guide stays under the 60 000-character context test** (doc 63).

## Found while building: a test left a job reading the database

- **The failure:** the full suite began to segfault intermittently, twice in a row, with
  nothing else running.
- **The cause:** faulthandler put the crash in a prep-job thread (`collect` inside the
  default-recipe job) while the main thread was in `reset_connection`.
- **The test at fault:** doc 102's MCP test started a default-recipe job and returned at
  once, so the next test's teardown closed SQLite under the running job.
- **The fix:** the test now polls the job to its end inside the app (an empty dataset
  fails with *"no images"*). Three full runs afterwards were clean.
- **A wrong guess, corrected:** the first two crashes happened while a SAM 3 job was
  training, and they were at first put down to memory. That was wrong, and the same crash
  repeated with nothing running.

## Verified (2026-09-30)

- **Tests:** the MCP contract lists 32 tools. A test adds a phrase with a variation and
  writes and reads the guideline over MCP. The guide test checks section 2d; the guide is
  27 702 characters.
- **Live MCP:**
  - `tools/list` names the six new tools.
  - `list_phrases` on the ring dataset returned blob (61) and ring (139). A list result
    comes back one content item per element, as every list tool here does.
  - `get_annotation_targets` returned the five targets.

## Bugs

(none yet)

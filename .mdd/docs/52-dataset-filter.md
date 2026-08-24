---
id: 52-dataset-filter
title: Filter Heads by What They Were Trained On
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: complete
depends_on: [34-inference-picker-upfront, 12-head-instance-registry]
relates: [51-library-tab, 37-foundation-model-in-viewer]
source_files:
  - apps/frontend/src/hooks/useHeadRun.ts
  - apps/frontend/src/components/HeadRunPanel.tsx
routes: []
models: []
test_files:
  - apps/frontend/src/components/HeadRunPanel.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [inference-viewer, filtering, head-picker, datasets, react]
path: Inference Viewer/Picker
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**Filters heads only.** Foundation models are listed separately and a fine-tuned one *does* carry `dataset_ids`, but the API's `FoundationInfo` does not expose them — so a fine-tune trained on the chess set stays visible under a chess filter."
  - "The two filters compose with AND and there is no indication when that combination is why the list is empty."
  - "A deleted dataset disappears from the filter even though heads still reference it, because the options are built from datasets that currently exist. Those heads then cannot be filtered to at all."
sister_projects: []
---

# 52 — Filter by Trained Dataset

## Purpose

> "not only enable filtering by tasks, but also by the trained dataset. So e.g. filtering
> for the chess set."

## Why the task filter was not enough

`task` answers "what kind of thing does this predict". After Waves 4–7.5 there are eighteen
heads and most of them answer `detection` — the filter stops discriminating exactly when
there are enough heads to need it. "Which data did this learn from" is the question that
still separates them.

`HeadInstance.dataset_ids` has carried the answer since doc 12; nothing was reading it.

## Business Rules

1. **The options are the datasets that heads were actually trained on**, intersected with
   the datasets that still exist. A filter offering a choice that matches nothing is a
   dead end the user has to discover by trying it.
2. **Names, not ids**, resolved against the dataset list. An id is not a thing a person
   recognises.
3. **The dataset list loads in its own effect.** A dataset list that fails should cost the
   filter, not the panel — the heads still run without it.
4. **The two filters compose.** Filtering by dataset alone is the common case and the one
   Jan asked for; combining them is free once both are predicates over the same list.

## Verified

**In the running app on 2026-08-21**: the filter offered exactly the five datasets that
heads had been trained on — the two OSDaR23 splits, Blood cells, Chess pieces, Thermal dogs
and people — and choosing *Chess pieces* narrowed the list from 26 entries to the 4
chess-trained heads.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

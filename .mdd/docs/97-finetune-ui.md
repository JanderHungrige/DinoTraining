---
id: 97-finetune-ui
title: Fine-Tune UI — Requirements, Readiness, and Before/After in the Training Tab
edition: DinoTraining
depends_on: [92-data-requirements-contract, 93-finetune-framework, 89-guided-preparation-flow, 90-training-consumes-recipe]
relates: [94-sam2-finetune, 95-dinov3-finetune, 96-sam3-finetune, 98-finetune-for-agents]
source_files:
  - apps/frontend/src/api/finetune.ts
  - apps/frontend/src/hooks/useFoundationFinetune.ts
  - apps/frontend/src/components/finetune/FoundationFinetunePanel.tsx
  - apps/frontend/src/components/finetune/FinetuneParts.tsx
  - apps/frontend/src/finetune.css
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/tabs/introContent.ts
routes: []
models: []
test_files:
  - apps/frontend/src/components/finetune/FoundationFinetunePanel.test.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.test.tsx
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [fine-tuning, frontend, requirements-card, readiness, before-after, training-tab]
path: Training/Fine-tuning/UI
initiative: dinotraining
wave: dinotraining-wave-12
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Disk and memory are not estimated before the click, as the wave asked; the requirements card shows the gates (SAM 3's memory, gating) and the time per picture in `what_trains`. A measured estimate per model would replace that."
  - "Example overlays of base vs fine-tuned are not shown in the panel; the numbers are. Doc 94 shows the overlay for SAM 2."
  - "Doc 44's `FinetunePanel`, `useFinetune` and their test are removed. The `/foundation/finetune` endpoint remains for compatibility; nothing in the app calls it."
security_read_sites: []
sister_projects: []
---

# 97 — Fine-Tune UI

## Purpose

The Training tab's "Fine-tune a model" mode now offers every fine-tunable model through
docs 92–93. Before anything trains, the user sees **what the model needs** and **whether
their data meets it**. Afterwards they see the base and the fine-tuned model **on the same
held-out pictures**.

## The panel (`FoundationFinetunePanel`)

1. **Model:** from `GET /finetune/requirements`. Models without an adapter are listed but
   disabled, marked "(not yet)".
2. **Dataset.**
3. **Requirements card** (doc 92), with:
   - the annotations and minimums;
   - how pictures are resized;
   - whether a recipe is needed;
   - the data format paragraph and why the minimums are what they are;
   - what trains;
   - the gates.
4. **Recipe:** doc 90's picker (the latest up-to-date recipe by default).
5. **Readiness:** `POST /finetune/check`, run again whenever the choice changes. Every rule
   is shown ✓ or ✗ with what was found and the fix.
6. **Settings:** rounds, and backbone blocks for DINO.
7. **Start**, enabled only when every rule passes. Then the progress ("measuring the base
   model first"), and Cancel, which now takes effect between pictures (doc 96).
8. **Result:** before (base) against after (best round) on the held-out pictures, with
   the notes ("nothing was saved: the base model is the better one", "optimistic: no test
   pictures").

Choices are remembered (doc 69). Lists, readiness and recipes are loaded, never seeded
into state.

## Claims corrected

The tab and the Intro quoted "mAP 0.96 against 0.5–0.6" for RF-DETR against a DINO head.
Those numbers came from random splits. The tab now says what Wave 12 measured on a
leak-free split: **0.62 against 0.41**. The Intro keeps the rail figures, marked as random
splits, next to the new ones.

## Verified live (2026-09-30)

In the running app, Training → Fine-tune a model → RF-DETR on the filled-ring set (masks
only):
- the card showed the box requirements;
- readiness showed ✗ on "The dataset has boxes", with the box data format as the fix;
- Start stayed disabled.

The panel test covers the enabled path: a DINO model starts with the recipe and
`unfreeze_blocks`.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

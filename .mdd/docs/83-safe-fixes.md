---
id: 83-safe-fixes
title: Safe Fixes — Reversible Exclusions and Class Maps
edition: DinoTraining
depends_on: [81-dataset-audit]
relates: [84-leakage-safe-split, 88-preparation-recipe, 90-training-consumes-recipe]
source_files:
  - backend/app/prep/fixes.py
  - backend/app/prep/state.py
  - backend/app/prep/stats.py
  - backend/app/prep/audit.py
  - backend/app/api/v1/prep_fixes.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/datasets/{dataset_id}/prep-state
  - POST /api/v1/datasets/{dataset_id}/fixes
models:
  - images.excluded (schema v9)
  - <dataset>/prep_state.json (class_map)
test_files:
  - backend/tests/test_prep_fixes_api.py
data_flow: writes-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, fixes, exclusion, class-map, reversible, non-experts]
path: Prepare Data/Fix
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts:
  - function: "training reads images.excluded and prep_state.class_map"
    when: "whenever samples are built for training or fine-tuning"
    satisfied_by: 90-training-consumes-recipe
satisfies_contracts: []
known_issues:
  - "Excluded images and the class map are honoured by the audit now, and by training only from doc 90 on. Until then a run trains on everything. Doc 90 is where the contract above is closed."
  - "Judgement fixes (blur, lighting, wrong labels) are not automated by design; the audit's examples are the review sheet. A 'look at these' viewer is doc 89's job."
security_read_sites: []
sister_projects: []
---

# 83 — Safe Fixes

## Purpose

The audit (doc 81) says what is wrong. This fixes what can be fixed **without any risk of
losing work**, and in a way a non-expert can undo.

## Rules

1. **Nothing is deleted.** Images are *excluded* (`images.excluded = 1`) and can be
   included again with one call.
2. **Classes are mapped, not rewritten.** Merging two classes in the data could never be
   undone, because nothing would remember which box was which. The map (`prep_state.json`,
   written name → class, or `null` to leave it out) is applied by training, and the stored
   boxes keep their original names. A test asserts the stored prompts are unchanged after
   a merge and a drop.
3. **The audit sees what training will see.** `collect()` leaves out excluded images and
   applies the map, so a re-audit after a fix shows the result.
4. **Copies: keep one.** The first image of every copy group from the last audit is kept,
   and the rest are excluded. Shared scenes (same picture, different annotations) are
   never touched: they are different examples (doc 81).
5. **Fixes that need findings need an audit:** `exclude-copies` and `exclude-unreadable`
   answer 409 "audit first" on a dataset never audited.
6. **An unknown path is refused by name** (422), never silently ignored.

## Actions

| action | does |
|---|---|
| `exclude` / `include` | take listed images out of training / back in |
| `exclude-copies` | keep one per copy group of the last audit |
| `exclude-unreadable` | exclude the files the last audit could not open |
| `set-class-map` | merge spellings, rename, or leave a class out (`null`) |

## Verified in the running app (2026-09-29)

On the test dataset "Wave 11 intake check" (20 chess images):
- **Audit:** 20 images, 12 classes, warns for size and thin classes, info for shared
  scenes, no copies (none in this sample, which is plausible for 20 of 289 photos).
- **Class map** `white pawns → white-pawn`: the re-audit lists `white-pawn` beside the
  other hyphenated names.
- **Exclusion:** excluding one image changed 1, including it again changed 1, and back to
  0 excluded. An unknown path gets 422.
- **Chess (289), not modified live:** 13 copy groups exist there. The API test proves the
  copy rule on synthetic copies and scene twins: 2 of 3 copies were excluded, and the
  scene twin with another class was kept.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

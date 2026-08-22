---
id: 51-library-tab
title: Library — Everything You Have Made, In One Place
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: complete
depends_on: [12-head-instance-registry, 44-finetune-rf-detr]
relates: [50-dataset-as-source, 35-model-licence-surfacing]
source_files:
  - backend/app/api/v1/foundation.py
  - backend/app/ml/foundation/build.py
  - apps/frontend/src/tabs/LibraryTab.tsx
  - apps/frontend/src/hooks/useLibrary.ts
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/tabs/introContent.ts
  - apps/frontend/src/App.tsx
  - apps/frontend/src/api/foundation.ts
  - apps/frontend/src/api/datasets.ts
routes:
  - DELETE /api/v1/foundation/instances/{instance_id}
models: []
test_files:
  - backend/tests/test_library_routes.py
  - apps/frontend/src/tabs/LibraryTab.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [library, organize, delete, datasets, heads, fine-tuning, react]
path: Library
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - backend/app/api/v1/foundation.py (instance ids build filesystem paths; PathConfinementError -> 400)
known_issues:
  - "**Read-only apart from delete.** Renaming needs routes that do not exist for datasets or heads, and a rule about what a rename does to provenance already recorded *inside* trained heads — a head stores `dataset_ids`, and its `summary` resolves them at render time. Jan chose browse-and-delete on 2026-08-21."
  - "**No export button**, though `POST /datasets/{id}/export/coco` exists. It belongs here and was left out with renaming to keep this one change."
  - "A dataset that a trained head references can be deleted, and the head then shows a raw id where a name was. The head still works — `dataset_ids` is provenance, not a dependency — but the display degrades silently."
  - "`isFineTuned` distinguishes an instance from a catalogue entry by `approx_size_mb === 0`. True by construction (nothing was downloaded for an instance) but it is an inference, not a field."
  - "No size on disk is shown. A fine-tune is 115 MB and a dataset with copied images can be far more; the thing most worth knowing before deleting is the thing not displayed."
sister_projects: []
---

# 51 — Library

## Purpose

One place that answers "what do I have, and what can I throw away?"

## Why it was needed

Datasets, trained heads and fine-tuned models were each reachable only from the tab that
produced them, and the store had drifted accordingly. Opening this tab for the first time
showed **21 datasets, 18 heads and 4 fine-tuned models** — including three datasets named
`i'p`, `;oo` and `l’kl;`, all with zero images, from mistyped fields during testing.

Two of the three had no way to delete anything at all: `FoundationInstanceStore.delete`
existed with nothing calling it, so a 115 MB fine-tune could be created and never removed.

## Business Rules

1. **Each list loads and fails independently**, and a failure names *which* list. The user
   is here to clean up and needs to know which list is incomplete before deleting anything
   based on it — "something went wrong" above a short list is worse than no list.
2. **Two clicks, and the second names the item.** A browser `confirm()` cannot say *which*
   row it is about, and this list is full of similarly-named things — four heads all read
   "Object detection: bishop +12 more".
3. **A catalogue model is not listed here.** Those are downloads managed in Admin / Models;
   the backend answers 404 for one, so offering it would be a button whose only outcome is
   an error telling you to go somewhere else.
4. **A head's own `summary` is shown**, never a second description composed here — doc 12's
   rule, and what stops one head reading differently in two places. `dataset_ids` *are*
   resolved to names, because an id tells the user nothing about which data it saw.
5. **The lists are re-read after every delete, including a failed one.** A delete that
   half-failed leaves the list lying about what is on disk, on the one screen where that
   matters most.
6. **The cached implementation is dropped on delete.** Without that, a model whose weights
   have just been removed keeps answering from memory until the process restarts — with
   results that look entirely normal.

## One bug, found by a test

The failure message was set **before** `refresh()`, and `refresh` ends by setting the error
to null when every list loads. So a failed delete showed *nothing at all*, and the row the
user had just tried to remove quietly reappeared — which reads as "it worked, then came
back". Setting it after the refresh is the whole fix.

## Verified

14 frontend tests and 11 backend. **Verified in the running app on 2026-08-21**: the tab
lists 21 datasets / 18 heads / 4 fine-tuned models, hides the catalogue entries, resolves a
head's dataset id to "Chess pieces", and the confirmation reads *Delete “i'p”*. Nothing was
actually deleted — that is Jan's data and his call.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

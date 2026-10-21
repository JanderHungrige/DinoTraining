---
id: 169-umbrella-box-classes-and-studio-scroll
title: Umbrella Terms Over Box-Only Classes, a Fresh Phrase List After Saving, and the Studio's Scroll Between Pictures
edition: DinoTraining
depends_on: [115-umbrella-terms, 116-phrase-bar-slim]
relates: [69-remembered-entries, 104-annotation-target]
source_files:
  - backend/app/datasets/phrases.py
  - backend/app/datasets/classes.py
  - apps/frontend/src/hooks/usePicturePhrases.ts
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/components/KeepHeight.tsx
routes: []
models: []
test_files:
  - backend/tests/test_umbrella_terms.py
  - apps/frontend/src/hooks/usePicturePhrases.reload.test.ts
  - apps/frontend/src/components/KeepHeight.test.tsx
data_flow: reads-existing
last_synced: 2026-10-21
status: complete
phase: all
mdd_version: 11
tags: [bugfix, umbrella-terms, phrases, annotation-studio, scroll]
path: Fixes/Studio/UmbrellaAndScroll
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 169 — Umbrella Terms Over Box-Only Classes, and the Studio's Scroll

## Jan (2026-10-21)

- "Umbrella terms cannot be entered. It always says it needs two classes, but when two
  classes are in the image, the user can still not add a phrase."
- "In the Annotation Studio, with each new image, the window goes back up; that disrupts
  the flow of annotating."

## 1. "Needs two classes" with two classes in the picture

- **Cause:** the phrase list (`PhraseStore.list_for`), which "+ Umbrella term" takes its
  classes from, read classes from outlines (masks) and the stored vocabulary only. **Classes
  that only label boxes were missing**, while creating an umbrella (`class_keys`) and the
  class picker (`ClassStore.list_for`) count them.
- **Measured on Jan's library** (read-only): 11 datasets had their classes only on boxes.
  The old list counted 0 or 1 classes there, so the form was blocked in all of them (Chess
  pieces 1 of 14, the OSDaR23 sets 0 of 3–7, Blood cells 0 of 3, …).
- **Fix:** the phrase list adds the box classes, from the same query as the class picker
  (`box_counts`, now public).
- **Second, smaller cause:** the Studio read the phrase list only when the dataset changed.
  A class made in the annotation list became a phrase on saving, but the bar did not know
  until the dataset was reopened. **Now read again on every picture and when a picture turns
  from unsaved to saved** (`usePicturePhrases(…, dirty)`).
- **Verified in the running app:** "Blood cells" and the OSDaR23 RGB set show
  "+ Umbrella term over the classes …" with all their classes.
- **A write during the check, undone:** starting a session in Grounding DINO mode stored its
  prompt "a cell" as a class of Blood cells; it was deleted at once (stored classes back to
  none, no box touched).

## 2. The window going back up between pictures

- **A real collapse, closed:** between pictures the Studio replaced the canvas and the list
  with one "Loading the image…" line, shortening the page by the picture's height. That can
  pull the scroll position up. `KeepHeight` keeps the area's last height while the next
  picture loads. Seen working with the large OSDaR23 pictures: the hold engages, and the
  position stays exactly.
- **Not reproduced as Jan's jump:** in the browser pane the position did not move even with
  the hold disabled, with or without scroll anchoring (which WebKit lacks). So the cause in
  Jan's setup is open; see known issues.

## Tests

- **Backend:** two classes only on boxes are listed as classes and take an umbrella. The
  test fails without the fix. Backend 1985.
- **Frontend** (1219 in total):
  - the phrase list is read again after a save and on the next picture;
  - `KeepHeight` keeps 640 px while a placeholder shows and lets go after.

## Confirmed (2026-10-21)

- Jan, after the merge: "jumping seems fine now". KeepHeight was the fix for his setup.

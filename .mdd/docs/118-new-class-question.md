---
id: 118-new-class-question
title: New-Class Question — "Does It Occur in the Pictures Already Saved?"
edition: DinoTraining
depends_on: [117-saved-means-complete]
relates: [119-add-only-review, 60-dataset-classes]
source_files:
  - backend/app/datasets/completeness.py
  - backend/app/api/v1/dataset_phrases.py
  - backend/app/mcp/annotation_tools.py
  - backend/app/i18n/de_errors.py
  - apps/frontend/src/api/phrases.ts
  - apps/frontend/src/components/NewClassQuestion.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/i18n/en/studio2.ts
  - apps/frontend/src/i18n/de/studio2.ts
  - apps/frontend/src/phrases.css
routes:
  - POST /api/v1/datasets/{dataset_id}/completeness/absent
models:
  - image_phrase_status
test_files:
  - backend/tests/test_completeness.py
  - apps/frontend/src/components/NewClassQuestion.test.tsx
  - backend/tests/test_mcp_server.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, completeness, classes, sam3, mcp]
path: Studio/Classes/NewClassQuestion
initiative: dinotraining
wave: dinotraining-wave-15-5
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 118 — New-Class Question

## Purpose

- **Jan:** "The new class from picture two on can be asked by a popup: 'does the class
  only occur from now on?' Then either all earlier pictures are *does not occur*, or
  *review later*."
- **Doc 117** already leaves such pictures unknown for the new class. This doc asks the
  user which of the two it is.

## When it asks

- **Where:** the Studio shows the question for **every class with unknown pictures**
  (doc 117's `/completeness`).
- **When it looks:** on opening a dataset, and whenever the vocabulary changes:
  - a class made in the list's picker;
  - a class arriving from the prompt (`usePromptClasses`, doc 117);
  - a class appearing on a saved picture.
- **Not a modal:** a banner above the canvas. The user may be in the middle of an outline,
  and a modal would take the keys.

## The question

> **m10 is new. 20 pictures were saved before it.** Does m10 occur in them?
> [It does not occur there] [Review them later]

- **It does not occur there:**
  - `POST /datasets/{id}/completeness/absent {class_name}` marks each of those pictures
    `absent` for the class (an explicit check, doc 103). They become known, and are
    confirmed negatives for SAM 3.
  - The banner says "20 pictures marked: no m10."
- **Review them later:**
  - Nothing is written; the pictures stay unknown (doc 117) and are left out for m10.
  - The answer is remembered per dataset and class in the viewer's browser, a convenience
    only.
  - The banner shrinks to one line, "m10: 20 pictures not reviewed yet", with **Review
    for m10** (doc 119).
- **Once no picture is unknown** for a class, its line disappears on its own, whether
  through the review, hand checks or re-saving.

## MCP

- `get_completeness(dataset_id)`: per class, `since` and `unknown`.
- `mark_absent_in_older_pictures(dataset_id, class_name)`: the first answer.
- The docstrings tell an agent to ask its user which of the two applies, and never to
  assume "does not occur".

## Rules

1. **"It does not occur there" never touches a picture that is already checked** or
   already known. It writes only the unknown ones.
2. **The question never blocks saving,** annotating or switching pictures.
3. **An unknown class name** in the POST is a 422 with the reason, translated.

## Verified (2026-09-30)

- **Tests:**
  - Backend, `test_completeness.py` (3 more):
    - "It does not occur there" marks only the unknown pictures, and a repeat marks 0;
    - training then reads them as `absent`;
    - an unknown class is refused in German.
  - The MCP contract lists `get_completeness` and `mark_absent_in_older_pictures`.
  - `NewClassQuestion.test.tsx` (3):
    - it asks only for a class with unknown pictures;
    - "does not occur" marks and looks again;
    - "review later" leaves a remembered reminder with "Review for".
  - Backend and frontend suites are green.
- **Running app, German (restarted backend):**
  - After creating class "star" with 70 saved pictures, the Studio showed "star ist neu.
    70 Bilder wurden davor gespeichert. Kommt star darin vor? …".
  - "Kommt dort nicht vor" answered "70 Bilder markiert: kein star." and the question
    disappeared.
  - The phrase "star", its 70 checks and the class were deleted again.

## Bugs

(none yet)

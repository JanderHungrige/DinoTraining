---
id: 104-annotation-target
title: Annotation Target — "What Will This Dataset Train?", Required and Optional Layers, a Checklist per Picture
edition: DinoTraining
depends_on: [103-phrase-data-model, 01-annotation-studio, 92-data-requirements-contract]
relates: [105-phrase-annotation-ux, 106-mask-editing, 107-task-aware-preparation, 110-annotation-for-agents]
source_files:
  - backend/app/datasets/annotation_targets.py
  - backend/app/api/v1/annotation_targets.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/annotationTargets.ts
  - apps/frontend/src/api/phrases.ts
  - apps/frontend/src/lib/pictureChecklist.ts
  - apps/frontend/src/components/AnnotationTargetPicker.tsx
  - apps/frontend/src/components/TargetGuide.tsx
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/targets.css
  - apps/frontend/src/components/DatasetChoiceRow.tsx
  - apps/frontend/src/hooks/useAnnotationTargets.ts
  - apps/frontend/src/hooks/useAnnotationTargetList.ts
  - apps/frontend/src/hooks/usePicturePhrases.ts
  - apps/frontend/src/api/datasetMasks.ts
  - apps/frontend/src/hooks/useBoxEditing.ts
  - apps/frontend/src/types/annotation.ts
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/annotation-targets
  - GET /api/v1/datasets/{dataset_id}/annotation-target
  - PUT /api/v1/datasets/{dataset_id}/annotation-target
models: []
test_files:
  - backend/tests/test_annotation_targets.py
  - apps/frontend/src/lib/pictureChecklist.test.ts
  - apps/frontend/src/components/TargetGuide.test.tsx
  - apps/frontend/src/components/AnnotationTargetPicker.test.tsx
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, targets, sam2, sam3, classification, detection, non-experts, onboarding]
path: Annotation Studio/Target
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "A picture's class is not a stored layer of its own: a classifier takes it from the picture's annotations (one class per picture; a picture with two is skipped). The checklist says which it is."
security_read_sites: []
sister_projects: []
---

# 104 — Annotation Target

## Purpose

Jan (2026-09-30): *"We should choose what we are annotating for. If we choose e.g. a SAM 3
model, we should also [create] phrase masks. We should always be able to annotate instance
masks, phrase masks and whatever else is needed, so even when we 'just annotate bounding
boxes' we can later use the dataset for SAM fine-tuning. But we do not want to force the
user. When choosing a model that only needs e.g. a class per image, make the other parts
optional and explain them. When choosing SAM 2, SAM 3, … the optional becomes a must."*

## Targets and layers

**Five targets:**
- keep all options open (**recommended**, the default);
- picture classifier;
- detector (boxes);
- instance outlines (SAM 2);
- concept outlines (SAM 3).

**Five layers:**
- one class per picture;
- boxes;
- outlines (masks);
- phrases;
- checked per picture.

| Layer | Open | Classifier | Detector | SAM 2 | SAM 3 |
|---|---|---|---|---|---|
| One class per picture | optional | **required** | optional | optional | optional |
| Boxes | recommended | optional | **required** | optional | optional |
| Outlines (masks) | recommended | optional | optional | **required** | **required** |
| Phrases | recommended | optional | optional | optional | **required** |
| Checked per picture | recommended | optional | optional | optional | **required** |

Every cell carries one sentence saying why, for this target. For example:
- **SAM 3 × Checked per picture:** "an unchecked picture teaches nothing; a checked empty
  one teaches 'not here'".
- **Detector × Outlines:** "optional — outlines keep this dataset usable for SAM later, one
  click from your boxes".

The matrix lives in the backend (`annotation_targets.py`), served by
`GET /annotation-targets`, so MCP relays the same words (doc 110).

**"Keep all options open" is cheap** — every recommended layer is nearly free:
- a class name is already a phrase (doc 103);
- outlines come from boxes in one click (doc 106).

## Storage

- **Where:** `datasets/<id>/annotation_target.json` holds `{target}`, read and written by
  `GET`/`PUT /datasets/{id}/annotation-target`.
- **Default:** a dataset that has never been set answers `open`.
- **Mapped profiles:** each target maps to a Prepare data profile — classifier → a
  classification head, detector → RF-DETR (nano), SAM 2 → SAM 2.1 (small), SAM 3 → SAM 3,
  open → none. Starting a session with a mapped target writes Prepare's remembered target
  (doc 69 key `prepare.target`), so Prepare data opens for the model being annotated for.

## UI

- **Setup:** `AnnotationTargetPicker` is a radio group, "What will this dataset train?".
  Each option has one line saying what it asks of you. The choice is remembered (doc 69,
  `studio.target`), and saved to the dataset on Start.
- **Studio:** `TargetGuide` is a folding panel under the counter, **"Annotating for: SAM 3"**.
  - It lists every layer with its level badge (required / recommended / optional) and its
    sentence.
  - **"This picture"** is the checklist (`pictureChecklist`) for the required and
    recommended layers:
    - **one class:** ✓ "One class: ring", or "Several classes (ring, blob): a classifier
      skips this picture";
    - **boxes:** ✓ "3 objects", or "Nothing marked yet";
    - **outlines:** ✓ "All 3 have an outline", or "1 of 3 have an outline";
    - **phrases:** ✓ "ring, red ring", or "No phrase yet";
    - **checked:** ✓ "Checked for all 2 phrases", or "Checked for 1 of 2 phrases".
  - A required layer that is not met is marked, and nothing is blocked. Saving stays
    possible, because partial work is normal.

## Business Rules

1. **Nothing is forced.** A target changes what is *marked required*, never what can be
   saved.
2. **The matrix is the one source of the wording,** for the UI and MCP.
3. **An unknown target is a 422.**

## Also in this feature: phrases survive the Studio

**The problem:** the Studio's save replaces an image's masks. Without carrying doc 103's
`phrases`, every re-save would have cleared a mask's phrase links.

**The fix:**
- `CanvasBox.phrases` is loaded from the stored masks and re-sent on save.
- **Renaming a box's class** drops the old class name from its phrases. Sent back, the old
  name would become a phrase of the new class, or be refused as another class's phrase.

`SessionSetup` reached the 300-line gate, so the dataset/new-name row moved to
`DatasetChoiceRow`.

## Verified (2026-09-30)

- **Tests:** backend 1746 green; frontend 1003 green; tsc, ruff and mypy app are clean.
- **Running app, setup:** "What will this dataset train?" appeared, styled like the choice
  beside it. Choosing *Concept outlines (SAM 3)* and starting on "Wave 12 filled-ring
  convention" stored `{"target": "sam3"}` for the dataset.
- **Running app, Studio:** the panel read "Annotating for: Concept outlines (SAM 3) · 1
  required still open on this picture".
  - It listed all five layers with their badges and sentences.
  - **This picture:** ✓ "Outlines (masks): All 4 have an outline", ✓ "Phrases: blob,
    ring", and ○ "Checked per picture: Checked for 0 of 2 phrases".

## Bugs

(none yet)

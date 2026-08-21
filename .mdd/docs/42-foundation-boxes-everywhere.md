---
id: 42-foundation-boxes-everywhere
title: Foundation Boxes Everywhere — Proposals Before Anything Is Trained
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: in_progress
depends_on: [41-rf-detr-detector, 25-expert-annotator, 33-studio-head-annotator]
relates: [22-mask-dataset-store, 29-generated-dataset-writer, 26-generator-review-ui]
source_files:
  - backend/app/ml/annotators/proposals.py
  - backend/app/ml/annotators/foundation.py
  - backend/app/ml/annotators/expert.py
  - backend/app/api/v1/generate_foundation.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/datasets/models.py
  - apps/frontend/src/api/foundation.ts
  - apps/frontend/src/components/FoundationPicker.tsx
  - apps/frontend/src/components/ProposalModePicker.tsx
  - apps/frontend/src/components/GeneratorModePicker.tsx
  - apps/frontend/src/components/MaskSourceFields.tsx
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/types/annotation.ts
routes:
  - POST /api/v1/generate/foundation
models:
  - boxes
test_files:
  - backend/tests/test_proposals.py
  - backend/tests/test_generate_foundation_api.py
  - backend/tests/test_migrations_v7.py
  - backend/tests/test_migrations_v7_fixtures.py
  - apps/frontend/src/components/SessionSetup.foundation.test.tsx
  - apps/frontend/src/components/GeneratorSetup.foundation.test.tsx
data_flow: writes-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [object-detection, proposals, provenance, migrations, annotation-studio, dataset-generator]
path: Annotation Studio/Proposals
integration_contracts: []
satisfies_contracts:
  - from: 41-rf-detr-detector
    function: "source_boxes_payload / Box(x>=0, fits_within)"
    when: "a foundation detector's proposals are saved into a dataset"
    status: done
    verified_at: "backend/app/ml/annotators/proposals.py — clamp_to_frame"
security_read_sites: []
known_issues:
  - "**Neither tab changes its default mode.** A general detector leads the *list* in both, which is where discoverability lives, but selecting it by default would drop someone with trained heads and no detector installed onto an empty state pointing at Admin. Deriving the default from what is installed would mean seeding state from an async fetch — this project's most-repeated bug. Worth revisiting once first-run state exists (doc 38 wanted it too)."
  - "The Generator's proposal count is per image and per press. A folder is still reviewed one image at a time; nothing batches a detector over the whole folder unattended."
  - "`clamp_to_frame` trims silently. A box trimmed from 641 px to 640 px is invisible to the reviewer, which is right; a box trimmed from 900 px to 640 px is a much bigger edit and looks the same. Only the count of *fully* outside boxes is logged."
sister_projects: []
---

# 42 — Foundation Boxes Everywhere

## Purpose

Let a foundation detector propose boxes in the **Annotation Studio** and the **Dataset
Generator**, not only in the Inference Viewer — so a first-time user gets useful proposals
before labelling or training anything.

## Architecture

Doc 41 made RF-DETR runnable; this makes it *usable*. Both tabs previously offered only
head instances whose `render_hint` is `boxes`, which meant the app's starting point was
"train something first" — backwards for a tool whose selling point is starting from
proposals.

```
                     ┌── /generate/expert      (a head you trained)
Annotation Studio ───┼── /annotate             (a phrase)
Dataset Generator ───┼── /generate/foundation  (a general detector)   ← new
                     └── /generate/masks       (a concept)
                                │
                    all produce list[Box] ──▶ one review surface ──▶ one save path
```

`generate_foundation.py` is a separate router module because `generate.py` reached **302
lines** with it included, past the 300-line gate. The split follows a real seam: that file
proposes from things the user *made* or *prompted*; this proposes from a model needing
neither.

## Data Model

One new provenance, and a migration:

| Change | Where |
|---|---|
| `"foundation-model"` in `PROVENANCE_VALUES` | `datasets/schema.py` |
| `LATEST_VERSION` 6 → 7 | `datasets/migrations.py` |
| `Provenance` literal, backend **and** the hand-mirrored frontend union | `models.py`, `annotation.ts` |

**`foundation-model` is the *kind*, not the model.** `producer` names which one — exactly
the split doc 29 set for `expert-head`. A value per model would grow the CHECK on every
catalogue addition and tell a reviewer nothing `producer` does not already say.

The version bump is load-bearing for the third time: `run_migrations` returns early once
the stored version reaches `LATEST_VERSION`, so widening the vocabulary without moving the
number rebuilds the CHECK on *fresh* databases only. `test_migrations_v7` starts from a
**stamped v6** database for that reason.

## Business Rules

1. **A proposal is clamped to the frame, never dropped for leaving it.** Detectors predict
   boxes that exit the image, legitimately — an object at an edge continues past it.
   Measured on RF-DETR: a `couch` box began at x=0.9 and ran **1.5 px past the right edge**
   of a 640×480 image. `Box` requires `x >= 0` and `fits_within`, so an unclamped proposal
   raises *after* the reviewer has judged it. Dropping instead of clamping would silently
   lose every true detection at a border.
2. **The same clamp fixes the expert path**, which had the same latent bug:
   `decode_ltrb_to_boxes` regresses unbounded distances from a cell centre, so a trained
   head can leave the frame too. Nobody had hit it; it was waiting.
3. **A depth model is refused with somewhere to go.** It is a foundation model and a
   perfectly good one — just not reviewable as boxes. The 409 names the Inference Viewer
   rather than only saying no.
4. **`render_hint`, never `task`**, decides what may be offered — doc 20's rule, applied to
   a third kind of thing.
5. **The proposal shape is identical to the expert route's.** A reviewer should not be able
   to tell which produced a box except by reading where it says it came from, so the review
   surface consumes one shape rather than two.

## Verified

End to end against real weights on 2026-08-20, and the live database migrated to **v7**
with its existing rows intact.

**Annotation Studio** → *A general detector* → RF-DETR → a two-image COCO folder →
**Run model** → 5 proposals → **Save**. Read back from SQLite:

```
foundation-model | cat    | 0.96 | 14.2,54.1,302.1,419.6  | 640x480
foundation-model | cat    | 0.91 | 347.0,26.2,292.1,348.9 | 640x480
foundation-model | remote | 0.91 | 334.2,76.9,37.0,111.2  | 640x480
foundation-model | remote | 0.88 | 40.2,73.5,135.6,44.5   | 640x480
foundation-model | couch  | 0.41 | 0.9,1.0,639.1,474.7    | 640x480
```

The last row is the clamp working: `0.9 + 639.1 = 640.0` exactly, where the raw prediction
ran to 641.5. Real COCO class names land in `prompt`, so the dataset is trainable on them.

**Dataset Generator**: all three modes offered, the general detector leading the list and
correctly *not* selected by default; choosing it reveals the detector picker.

## Security

No new user-supplied input. `foundation_id` is a registry key, `image_path` goes through the
existing `read_image`.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

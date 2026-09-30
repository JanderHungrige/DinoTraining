---
id: 82-external-data-intake
title: External Data Intake — Check an Export Before Importing It
edition: DinoTraining
depends_on: [31-external-dataset-import, 81-dataset-audit]
relates: [84-leakage-safe-split, 89-guided-preparation-flow]
source_files:
  - backend/app/prep/intake.py
  - backend/app/prep/intake_findings.py
  - backend/app/datasets/bbox_conventions.py
  - backend/app/datasets/class_names.py
  - backend/app/datasets/coco_import.py
  - backend/app/datasets/models.py
  - backend/app/datasets/images.py
  - backend/app/datasets/store.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/api/v1/prep_intake.py
  - backend/app/api/v1/datasets.py
  - backend/app/api/v1/router.py
routes:
  - POST /api/v1/datasets/import/coco/inspect
  - POST /api/v1/datasets/import/coco (adds box_convention, class_map, keep_source_split)
models:
  - images.split (TEXT, nullable) — schema v9
  - images.excluded (INTEGER, nullable) — schema v9, used by doc 83
test_files:
  - backend/tests/test_prep_intake.py
  - backend/tests/test_migrations_v9.py
data_flow: mixed
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, coco, import, bounding-boxes, class-names, splits]
path: Prepare Data/Intake
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The merge proposal takes the most frequent spelling as canonical. On the real check it proposed 'white pawns' while every other class uses hyphens. The flow (doc 89) must let the user pick the canonical name; the API already takes any class_map."
  - "Only COCO is inspected. The OpenLABEL path (doc 49) has no route and writes images without sizes, and it stays as it was."
  - "Sizes are compared for the first 200 images per file. An export whose later images are wrong would pass."
  - "An unchecked import of a corner-coordinate file keeps the boxes that happen to fit when misread, 111 of 273 in the real check, and they are wrong. The import route cannot tell. Only the inspection can, which is why the flow always inspects first."
security_read_sites:
  - backend/app/prep/intake.py:_inspect_file (file_name from third-party JSON, confined with ensure_within)
sister_projects: []
---

# 82 — External Data Intake

## Purpose

External data is where preparation matters most: the Generator's datasets have known
conventions by construction, and an export from elsewhere has only its claims. The intake
reads a COCO export **without writing anything** and reports what it really contains. The
import then applies exactly what was checked.

## Architecture

```
POST /datasets/import/coco/inspect {directory}     writes nothing
  per annotation file: images, annotations, missing images, size mismatches (first 200),
                       box evidence: share valid as x,y,w,h / as x1,y1,x2,y2 / normalised
  decide()          → the convention the evidence supports, or null when it is ambiguous
  propose_merges()  → written name → class, for spellings of one class (spelling_key)
  split_of(folder)  → train / val / test from Roboflow-style folders
  intake_findings() → plain-language findings (doc 81's Finding shape)
POST /datasets/import/coco {…, box_convention, class_map, keep_source_split}
  ImportOptions → to_xywh() per box, class_map per name, images.split per folder
```

## Business Rules

1. **Evidence, not assumption.** `xywh` needs 98 % of boxes valid when read that way.
   `xyxy` needs 98 % valid as corners *and* under 90 % as `xywh`, so COCO's own convention
   wins a tie, since it is the file's claim. Every value ≤ 1 means normalised. Anything else
   is **ambiguous**, reported as a problem, and never guessed.
2. **Merges are proposals.** `spelling_key` unifies separators and a plural *s*; the most
   used spelling is proposed. `glass`/`glasses` share a key, so a merge is never silent.
3. **A kept source split is written to `images.split`** (schema v9). An import that omits
   it never clears a split already stored (COALESCE), as doc 73 does for frame positions.
4. **`file_name` is third-party text**, confined to the export folder with `ensure_within`
   during inspection too, not only at import.
5. **Bad input is a 422**, never a 500.

## Verified in the running app (2026-09-29)

A real export was built from 20 chess images with their stored boxes, written as corner
coordinates, with `white-pawn` spelled two ways, in `train/` and `valid/` folders:

- **Inspect:** convention `xyxy`, with evidence of 38 % / 43 % valid as `xywh` vs 100 % as
  corners, per folder; split `train` / `val`; merge proposed. Findings: warn (spellings),
  info (converted), info (already split).
- **Import as checked:** 20 images, **273 boxes, 0 skipped**, one pawn class, split kept.
- **Import unchecked** (plain COCO): it reported success with **162 of 273 boxes silently
  dropped**, and the 111 it kept were misread. That is the failure this doc exists to
  prevent.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

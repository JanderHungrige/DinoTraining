---
id: 85-model-input-planning
title: Model Input Planning — What the Model Sees, and Whether to Tile
edition: DinoTraining
depends_on: [10-preprocessing-pipeline, 62-tiled-inference, 81-dataset-audit, 83-safe-fixes]
relates: [49-osdar23-rail, 44-rfdetr-finetune, 81-dataset-audit, 88-preparation-recipe, 89-guided-preparation-flow, 90-training-consumes-recipe]
source_files:
  - backend/app/prep/input_plan.py
  - backend/app/prep/input_preview.py
  - backend/app/prep/profiles.py
  - backend/app/prep/findings.py
  - backend/app/api/v1/prep_input.py
  - backend/app/api/v1/router.py
routes:
  - GET /api/v1/datasets/{dataset_id}/input-plan
  - POST /api/v1/datasets/{dataset_id}/input-preview
models: []
test_files:
  - backend/tests/test_prep_input_plan.py
  - backend/tests/test_prep_input_api.py
  - backend/tests/test_prep_profiles.py
  - backend/tests/test_prep_findings.py
data_flow: reads-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, preprocessing, input-size, letterbox, stretch, tiling, preview, non-experts]
path: Prepare Data/Model Input
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts:
  - function: "training and fine-tuning cut the planned tile grid (plan_tiles, same overlap) before building samples"
    when: "a recipe carries a recommended tiling"
    satisfied_by: 90-training-consumes-recipe
satisfies_contracts: []
known_issues:
  - "A file read that blocks stalls the preview request with no timeout. Seen live: the first read under ~/Downloads waited on macOS's privacy check, and the request took 6,711 s; every later one took 0.0–0.4 s."
  - "SAM 2's processor trains masks at 256×256 (mask_size), a quarter of its 1024 px input. Outline detail finer than about 4 input pixels is lost, and the plan does not say so yet. Wave 12 (SAM fine-tuning) owns that."
  - "Tiling is offered for box targets only. Outlines would need cutting with the image; whole-image labels cannot be tiled truthfully."
  - "Audits stored before 2026-09-29 judged RF-DETR and SAM 2 as letterboxed (see Bugs). Re-run them."
security_read_sites:
  - backend/app/prep/input_preview.py:render (opens sampled image files of the dataset)
sister_projects: []
---

# 85 — Model Input Planning

## Purpose

Every model shrinks a picture to a fixed size before looking at it. For someone who has
never trained a model, "the objects arrive at 1.7 px" means nothing. A 384 px picture
in which the signal is two grey pixels means everything. This feature works out what the
chosen model does to the dataset, decides whether to tile, and shows sampled images
**exactly as the model gets them**.

## Architecture

```
GET  /datasets/{id}/input-plan?target=&grid=     prep/input_plan.py (pure, over DatasetFacts)
POST /datasets/{id}/input-preview {target, grid?, count, seed}
                                                 prep/input_preview.py (opens files)
```

Both see the dataset as training will: excluded images left out and the class map
applied (doc 83).

## The plan

| Field | Meaning |
|---|---|
| `fit` | `letterbox` (shrink the long edge, pad to a square), `stretch` (squeeze into a square), `shortest-edge`, or `center-crop` (classification only) |
| `fit_explained` | the same, in one plain paragraph |
| `padding_share` | share of the input that is padding, for the typical image (letterbox only) |
| `objects` | median and 10th-percentile object size **at the input**, the size needed (`2 × cell`), and the share too small to learn |
| `tiling` | recommended or not, `columns × rows`, the object sizes with that grid, and the reason |
| `masks` | how outlines follow the picture (nearest-neighbour, padding marked *ignore*) |

**Tiling rule:** take the smallest grid, from 1 up to 6 tiles along the long edge, that
brings the smallest tenth of objects to the size the model needs. If even 6 is not
enough, it recommends 6 and says the objects are **still too small**. Tiles are cut by
`plan_tiles`, the definition docs 49 and 62 already share, with the same overlap. `grid`
overrides the choice, and `grid=1` turns tiling off and states what that costs.

The audit's "objects too small" finding (doc 81) now uses this same arithmetic, so the
audit and the plan cannot disagree.

## The preview

- **Sampling:** half the images holding the smallest objects, the rest at random (seeded).
- **Tiled plans** show the tile holding the image's smallest object. Objects in other
  tiles are not counted as lost.
- **Real geometry:** letterbox and centre crop go through doc 10's `apply_geometry`,
  `transform_boxes` and `transform_mask`. A stretch is applied as the Hugging Face
  processor does it, with x and y scaled apart.
- **Drawing:** boxes in class colours (distinct for any number of classes), objects the
  model cannot see in red, outlines tinted.
- **Resolution:** returned at the model's own input size. The UI (doc 89) enlarges it
  without smoothing, so the user sees the pixels the model gets.
- **Counts:** per image, `objects`, `lost` (cut away by a crop) and `too_small`.
- **Unreadable files** are skipped and listed. They are never a 500.

## Verified live (2026-09-29)

| Dataset → target | Fit | Objects at input (median / p10, needed) | Tiling |
|---|---|---|---|
| OSDaR23 train → RF-DETR | stretch | 8.8 / 6.8 px, needs 16; 91 % invisible | 3×3 → p10 17.5 px |
| OSDaR23 train → DINOv2 detection head | letterbox | 10.1 / 7.8 px, needs 28; 100 % invisible | 5×5 → p10 34.0 px |
| Blood cells → RF-DETR | stretch | 70.7 / 56.1 px | none needed |
| Vegetation_track → SAM 2.1 | stretch | 376.9 / 14.5 px, needs 32 | not for outlines; told to crop |
| Chess → DINOv2 classification | centre crop | — | not for labels |

Every preview returned in 0.0–0.4 s after the first file access. The pictures were
checked by eye:
- **OSDaR tile:** the enlarged, blurred tile the model gets, with boxes on the signals.
- **SAM 2.1:** a 3:2 frame squeezed into the 1024 square, masks following, and the far
  signal marked red.
- **Blood cells:** boxes on every cell.

## Bugs

**RF-DETR and SAM 2 were judged as letterboxed; they stretch** (found live 2026-09-29).
- **Cause:** both processors carry `size: {height, width}`, and `profiles._from_processor`
  read that as a letterbox. Transformers' documentation for that form: resized to the
  exact size, aspect ratio **not** kept.
- **Consequence:** object sizes for wide frames were off, and the preview would have
  shown padding the model never sees.
- **Fix:** a `stretch` fit. Its size scale is the geometric mean of the two axis scales,
  which is exact for an object size measured as the root of its area. Both models now
  default to stretch, and the preview stretches.
- **Tests:** geometry pinned per fit by the rendered pixels.

**Three more, all from the first live run:**
- **Lost objects on a tile:** a tile reported "lost 4 of 8", but those 4 were in other
  tiles.
- **Boxes on a classifier:** a classifier was shown "32 too small" for boxes it never
  learns from.
- **Colours:** they repeated after seven classes.

Each has a regression test.

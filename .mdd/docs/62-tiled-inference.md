---
id: 62-tiled-inference
title: Tiled Inference — Run the Grid the Head Was Trained On
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [49-osdar23-rail, 16-inference-engine, 18-multi-head-compose, 43-detection-localisation]
relates: [21-same-task-head-compare, 33-studio-head-annotator, 12-head-instance-registry]
source_files:
  - backend/app/ml/inference/tiled.py
  - backend/app/ml/inference/compose.py
  - backend/app/api/v1/inference.py
  - backend/app/api/v1/generate.py
  - backend/app/ml/heads/store.py
  - backend/app/api/v1/heads.py
  - apps/frontend/src/api/inference.ts
  - apps/frontend/src/api/headInstances.ts
  - apps/frontend/src/components/TilingField.tsx
  - apps/frontend/src/components/HeadRunPanel.tsx
  - apps/frontend/src/hooks/useHeadRun.ts
  - apps/frontend/src/styles.css
routes:
  - POST /api/v1/inference/compose
  - POST /api/v1/generate/expert
models: []
test_files:
  - backend/tests/test_tiled_inference.py
  - apps/frontend/src/components/TilingField.test.tsx
data_flow: reads-existing
last_synced: 2026-08-25
status: complete
phase: all
mdd_version: 11
tags: [inference, tiling, small-objects, detection, nms, osdar23, inference-viewer]
path: Inference Viewer/Tiling
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 62 — Tiled Inference

## Purpose

Run a head over the **same grid it was trained on**. Doc 49 tiles images on the way in;
nothing tiled on the way out, so a head trained on 616 px tiles found nothing on a full
2464 px frame and said nothing about why.

## The arithmetic, restated

Doc 49 measured it: OSDaR23's median annotated object is **10.7 px across in a 2464 px
frame**. At a 448 px model input that object arrives as **1.9 px** — below the 7 px stride
the detector predicts on. It is not a hard example, it is *not in the tensor*.

A 4x3 grid gives 616 px tiles, in which the same object is 10.7 px of 616, and at 448 px
input **7.8 px** — above the stride, so representable. That is the whole reason tiling
exists, and it applies identically at inference. A head that learned to find a 7.8 px
object will not find a 1.9 px one.

**The failure is silent**, which is what makes it the worst gap in the project: the run
succeeds, the pass count is right, the elapsed time is right, and the answer is an empty
list. Nothing distinguishes it from an image with nothing in it.

## Where the setting lives

**Per run, and it is not a property of the head.** The same head should be runnable either
way: a tile-trained head over a single close-up crop wants no grid, and a whole-frame head
over a huge image might still benefit from one. Making it a head attribute would take a
legitimate choice away from the person who can actually see the picture.

Recording it on the *dataset* and inheriting it was the alternative, and it was rejected on
two grounds. It needs a schema change — a dataset records `id, name, created_at, prompt,
copy_images` and nothing about how it was built — and a head trained on two datasets with
different grids has no answer. The backlog's own note called it "more automatic and more
surprising", and surprising wins that trade only when the automatic answer is always right.

**But undiscoverable is its own failure.** So the app says when it thinks tiling is needed:
a head records the datasets it trained on, and those datasets' images record their width, so
"this head trained on 616 px images and you are running it on 2464 px" is a query, not a
guess. The hint appears next to the control; it never turns it on.

## Architecture

```
run_tiled(image, grid)
  │
  ├─ plan_tiles(w, h, columns, rows, overlap)      the SAME planner doc 49 tiles with
  ├─ image.crop(tile)  per tile
  ├─ prepare_images(plan, tiles)                   ONE batched backbone pass
  ├─ extract(backbone, pixel_values)               → BackboneFeatures (B, …)
  │
  └─ per tile:  slice features to batch 1
                predict_from_features(...)         → boxes in TILE coordinates
                offset by (tile.x, tile.y)         → FRAME coordinates
     merge:     batched_nms across the union       → one Prediction
```

**One backbone pass, not one per tile.** `prepare_images` already takes a list and
`BackboneFeatures` is batched throughout, so the expensive part is paid once. Decoding stays
per tile because `boxes_payload` masks over a flat score vector and a batched one would
flatten across images.

**`plan_tiles` is called, never reimplemented.** `tiling_images.py` already records why:
"the two must agree or the result is silently wrong". An inference grid that differed from
the training grid by a rounding rule would put every box slightly off, and nothing would
raise.

## Business Rules

1. **Boxes only.** This is where the gap is, and merging boxes has a right answer that
   already exists. A tiled depth map would show its seams; a tiled label map is a real
   feature but a different one. A non-box head with tiling requested runs whole-frame rather
   than failing — the request is coherent, it just has nothing to do.
2. **Merged with class-aware NMS**, the same `batched_nms` and the same `NMS_IOU_THRESHOLD`
   doc 43 uses within a tile. Overlap exists so an object on a seam is whole in *some* tile;
   the cost is that it is found twice, and NMS is what that costs.
3. **The overlap default is doc 49's**, for the same reason the planner is shared: a grid
   that differs from the training grid is a different grid.
4. **Coordinates come back in frame space**, so nothing downstream learns that tiling
   happened. The overlay, the review list and the store all see one image's boxes.
5. **A 1x1 grid is not an error, it is the whole frame** — and it must go down the same path,
   or the tiled and untiled answers would differ for reasons nobody could see.
6. **The hint never acts.** It says what the app knows — trained on N px, running on M px —
   and leaves the decision alone. A control that silently turned itself on would make two
   runs of "the same" configuration differ.

## API

Both routes take the same optional block. Absent means whole-frame, which is what every
existing caller sends.

```json
{ "tiles": { "columns": 4, "rows": 3, "overlap": 0.2 } }
```

* `POST /api/v1/inference/compose` — the Inference Viewer.
* `POST /api/v1/generate/expert` — the Annotation Studio's head proposals, which hit the
  identical wall when auto-annotating a full frame.

`422` for a grid below 1x1 or an overlap outside `[0, 1)` — `plan_tiles` already raises
`ValueError` for both, so the existing backstop carries it.

### The hint's data

`HeadInstanceInfo` gains `trained_width: int | null` — the **median** width of the images in
the datasets the head trained on. Median rather than mean because a dataset of tiles has one
consistent size and an outlier should not move it; null when the datasets are gone, which is
possible and must not break the listing.

## Data Flow

```
image (2464x1600)
  → plan_tiles                     12 tiles of 616x533
  → prepare_images                 (12, 3, 448, 448)
  → extract                        BackboneFeatures(cls=(12,D), patches=(12,C,32,32))
  → predict_from_features x12      boxes in tile coordinates
  → + (tile.x, tile.y)             boxes in frame coordinates
  → batched_nms                    one Prediction, frame coordinates
```

Unchanged: the payload shape, the overlay, the review list, the store. Only the numbers
inside `boxes` differ, and they differ by being correct.

## Dependencies

* `49-osdar23-rail` — `plan_tiles`, the grid, and the measurement that motivates all of it.
* `16-inference-engine` / `18-multi-head-compose` — `predict_from_features` and the shared
  pass this extends rather than forks.
* `43-detection-localisation` — `batched_nms` and the IoU threshold.

## Security

No new input reaching the filesystem or the network. The grid is three numbers, bounded by
`plan_tiles`'s own validation, and a large grid costs compute rather than memory — tiles are
cropped and batched, never all decoded at once.

## Verified

**In the running app on 2026-08-25**, against the data the gap was found in — an OSDaR23
`rgb_center` frame, 2464x1600, and a head whose `trained_width` reads **472 px**, which is
exactly the tile size doc 49 names.

```
score_threshold   whole frame     4x3 tiled
0.30              0 boxes         0 boxes
0.05              0 boxes         6 boxes
```

The six are `signal`, **13–17 px across**, clustered at (1306–1510, 761–808) — the far-field
signal gantry, in real frame coordinates. Doc 49 measured the median annotated object at
10.7 px; these are precisely the objects that are not in the tensor at whole-frame scale.
The untiled run finds none of them at **any** threshold down to 0.05, which is the silent
failure restated as a number.

The hint, on the same pair:

> This head trained on 472 px images and this one is 2464 px. Objects arrive about 5.2×
> smaller than it learned to find — tiling is probably needed.

Ticking it offered 5x4, which is 2464/472 rounded, and the hint dropped its "probably
needed" clause while keeping the explanation. The backend logged
`Tiled 5x4 over 2464x1600: 20 tile(s), 1 head(s) in 1302 ms` — so the grid survives the
UI → hook → client → API path, which is the seam a stale closure broke once already.

## Known Issues

- "**The Studio's foundation proposals do not tile.** `/generate/expert` takes the grid and
  `/generate/foundation` does not. A foundation detector brings its own preprocessing and
  was not trained on this project's tiles, so the grid has less to say about it — but RF-DETR
  on a 2464 px frame has the same arithmetic problem and no way to ask for help."
- "**The hint needs the heads to agree.** Two selected heads trained at different sizes give
  `trained_width: null` and no hint at all, rather than one hint per head. One number cannot
  describe two answers, and the panel has one row."
- "**Nothing tiles masks or depth.** Rule 1, and it is a real limit now that a segmenter can
  be trained here: a segmentation head trained on tiles has exactly this problem and runs
  whole-frame regardless."
- "**A large grid is slow and nothing says so.** 20 tiles is 20 decodes; the batched backbone
  pass is shared but the per-tile head forward is not. There is no progress and no warning
  at, say, 16x16 = 256 tiles."
- "**`trained_width` is a median over whole datasets.** A dataset mixing tiles and full
  frames reports something in between, and the hint is then wrong in both directions."

## Bugs

(none yet — populated by /mdd bug when issues are reported)

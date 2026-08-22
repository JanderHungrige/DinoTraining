---
id: 49-osdar23-rail
title: OSDaR23 — OpenLABEL, Tiling, and a Rail Detector
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: complete
depends_on: [31-external-dataset-import, 43-detection-localisation, 44-finetune-rf-detr]
relates: [11-training-job-runner, 48-dataset-format-guide]
source_files:
  - backend/app/datasets/openlabel.py
  - backend/app/datasets/openlabel_to_coco.py
  - backend/app/datasets/tiling.py
  - backend/app/datasets/tiling_images.py
routes: []
models: []
test_files:
  - backend/tests/test_openlabel.py
  - backend/tests/test_tiling.py
data_flow: writes-new
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [openlabel, osdar23, rail, tiling, small-objects, dataset-import, asam]
path: Datasets/Import
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - backend/app/datasets/openlabel.py (frame URIs become file paths; the leading slash is stripped)
known_issues:
  - "**`track` is excluded, and Jan asked for it.** OSDaR23 annotates track as an *open polyline* running to the horizon. Its bounding box is a huge diagonal rectangle containing mostly ballast and vegetation; training on it would teach the detector that `track` means most of the image and would poison every other class's background. Detecting rails needs segmentation or line detection, not boxes."
  - "**`signal` boxes are derived from closed `poly2d` quads**, not from `bbox` — OSDaR23 gives signals no `bbox` at all. The quad is tight, so the extent is a fair box, but it is a conversion rather than a published annotation."
  - "**538 of 1470 boxes were dropped as under 4 px.** They are real annotations of real objects; nothing here can learn from a 2 px patch, and each one would cost a detector a false negative it could never avoid. The count is reported rather than hidden."
  - "**One subsequence, 98 frames.** `12_vegetation_steady_12.1` is the resource Jan linked. The other 44 subsequences are the same format and the same code reads them; the 9.84 GB per subsequence is the limit, not the code."
  - "The prepare script is not in the repo — it is invocation, and the rules it invokes are in the app with tests. Reproducing it means re-running the pipeline in the doc below."
  - "**The holdout is honest but the early stopping was not.** Both models were selected on an internal random split of frames 0-77, which still contains near-duplicates. The holdout number is therefore validation-grade rather than test-grade."
  - "**A random image split is wrong for video, and the job runner does not know that.** `split_indices` splits by image, which is right for the three photo datasets and leaks badly on a 10 Hz sequence. Splitting by contiguous segment was done by hand here; nothing in the app offers it."
  - "Tiling has no inference-side counterpart. A trained rail head runs on a 472 px tile, not on a 2464 px frame; running it on a full frame will find nothing. Tiled *inference* is not implemented."
sister_projects: []
---

# 49 — OSDaR23

## Purpose

Train a head and a fine-tuned RF-DETR on a real rail dataset, and build the two things that
took to be possible: an **OpenLABEL** reader and a **tiler**.

## Getting 652 MB out of a 9.84 GB archive

The subsequence Jan linked is **9.84 GB**, and this machine had **14 GB free** — so
downloading it and then deleting the lidar does not fit, and the server **ignores HTTP Range
requests** (verified: a range request returns 200 and the whole file), so fetching only the
wanted members is not an option either.

Reading the ZIP **sequentially by its local file headers** solves both: one pass over the
network, decompressing only `rgb_center/` and the labels and discarding everything else as
it goes past. That *is* the "remove the LiDAR part" step, done at download time.

```
DONE kept=102 (651.8 MB) skipped=1296 streamed=9.84 GB
```

## OpenLABEL is not COCO

OSDaR23 publishes ASAM **OpenLABEL**: one file per subsequence describing every object
across every sensor, each annotation tagged with the `coordinate_system` it belongs to.
Doc 31's importer reads COCO and nothing else, so this **converts** rather than adding a
second import path: OpenLABEL → COCO → the importer that already exists.

Three rules are the whole converter, and each one silently produces a plausible dataset if
it goes the other way:

1. **One camera at a time.** The same physical object is annotated separately in every
   sensor that sees it. Ignoring `coordinate_system` would multiply every object by the
   sensor count *and* pair one camera's boxes with another camera's images. On this file
   that is 2,494 annotations correctly skipped for `rgb_center`.
2. **Centre-based to corner-based.** OpenLABEL's `bbox.val` is `[cx, cy, w, h]`; COCO's is
   `[x, y, w, h]` from the top-left. Missing it shifts every box by half its own size —
   small enough to read as ordinary annotation noise.
3. **A closed `poly2d` is a box; an open one is not.** Signals are closed four-point quads,
   so their extent is a fair box. `track` is an open polyline to the horizon, and its
   extent is mostly ballast.

## The measurement that decided the camera and the tiling

| camera | frame | boxes | median object | ratio | at 448 px input |
|---|---|---|---|---|---|
| rgb_center | 2464×1600 | 932 | 10.7 px | 0.43% | **1.9 px** |
| rgb_highres_center | 4112×2504 | 1232 | 16.5 px | 0.40% | 1.8 px |
| ir_center | 640×480 | 490 | 14.4 px | 2.25% | 10.0 px |
| rgb_left / right | 2464×1600 | **0** | — | — | — |

Two things fall out of this table.

**The side cameras carry no box annotations at all.** "All RGB cameras" would have added
images and no supervision — so Jan's choice of the centre camera was the only one that
worked, though not for the reason either of us gave.

**A 10.7 px object in a 2464 px frame arrives at the model as 1.9 px** — below the 7 px
stride doc 43's detector predicts on. No loss function and no number of epochs recovers an
object smaller than one cell; it is simply not in the tensor. Training on this camera
as-published was guaranteed to produce nothing, and would have looked like a modelling
failure rather than an arithmetic one.

## Tiling

A **6×4 grid with 15% overlap** gives 472 px tiles, in which the same object is 2.26% —
**10.1 px at the model's input**, above the stride.

Two rules, both of which fail by producing *more* data, which looks like success:

- **A box belongs to exactly one tile: the one whose centre is nearest.** "The tile its
  centre falls in" is not enough, and a test caught that — tiles overlap by design, so a box
  in the shared strip has its centre inside *two* of them and would be emitted twice.
- **Empty tiles are kept, but capped.** Sky and ballast are the background the detector must
  learn to reject, so dropping them teaches it that every image contains something. Keeping
  all of them is the opposite mistake: **every one of the 932 boxes lands in grid cell
  `r1c2`** — the camera is fixed on a train, so the objects are always at the vanishing
  point — and an uncapped 4×3 grid gave **1078 empty tiles to 98 useful ones**. The cap is
  one background tile per tile with a box, sampled evenly across the sequence.

## The pipeline, end to end

```
stream 9.84 GB, keep rgb_center + labels        102 files, 651.8 MB
convert  rgb_center, exclude track              98 frames, 932 boxes, 3 classes
         skipped 2494 other-sensor, 538 tiny, 0 open polylines
retile   6x4, overlap 0.15, background 1:1      392 tiles, 932 boxes, 196 empty, 0 unplaced
write    only the tiles the document names      392 images, 143 MB
import   POST /datasets/import/coco             392 images, 932 boxes, 0 skipped
```

Class counts after conversion: **signal 650, person 196, signal_pole 86.**

## The first numbers were wrong, and why

The first run reported **head 0.498** and **fine-tuned RF-DETR 0.957**. Both are inflated,
and the cause is in the data rather than in the code.

**OSDaR23 is a video sequence.** 98 frames at 10 Hz from a train, and this subsequence is
named `vegetation_steady` for a reason. Measured directly: consecutive frames at the same
grid position differ by **0.4 of 255** in mean absolute intensity — they are the same
picture. Splitting randomly by image, which is what doc 11's runner does and what is right
for the three reference datasets, puts near-identical twins in both halves. The validation
number that comes back is close to a training number.

Doc 11's rule was "split by image, not by box", because boxes from one image in both splits
is leakage with no symptom. **Video needs the rule one level up: split by segment, not by
frame.** The runner does not know that, and nothing in the pipeline could have noticed —
which is exactly why it is worth writing down.

So both models were retrained on **frames 0–77** and scored on **frames 78–97**, which the
sequence never showed them.

## Measured, on frames the models never saw

| | mAP | mAP@50 | mAP@75 |
|---|---|---|---|
| head — random split (leaky) | 0.581 | 0.725 | 0.437 |
| **head — temporal holdout** | **0.339** | **0.399** | **0.278** |
| RF-DETR — random split (leaky) | 0.955 | — | — |
| **RF-DETR — temporal holdout** | **0.857** | **0.979** | **0.736** |

Three things are worth reading carefully.

**Leakage cost the head 42% and the detector 10%.** A model with more capacity to memorise
should suffer *more* from a leaky split, not less; that it is the other way round says the
head was leaning on the near-duplicates for most of what it knew.

**RF-DETR is not slightly better here, it is in a different class** — 0.857 against 0.339.
Doc 44 measured the same comparison on thermal and found **identical mAP@50** (0.818 vs
0.817): both found the objects equally well and only placement differed. Here the detector's
mAP@50 is **0.979 against the head's 0.399**. The head is not misplacing these objects, it
is *missing* them.

That is the honest limit of a frozen backbone with a light head, found by running it: 10 px
far-field objects on cluttered natural background are the case where DINOv2 patch features
alone do not separate signal from vegetation, and a decoder trained to attend does.

**These are still validation-grade numbers, not test-grade.** The holdout was used once, but
the models' own early stopping ran against an internal (still random, still leaky) split of
frames 0–77.

For comparison, doc 43's datasets — collections of distinct photographs, where a random
split is sound:

| | mAP | mAP@50 | mAP@75 |
|---|---|---|---|
| thermal | 0.587 | 0.818 | 0.338 |
| blood | 0.550 | 0.775 | 0.325 |

## Why `track` is not in the model

Jan listed it, with 1,666 annotations. It is excluded and the reason is in the data: an open
polyline whose extent spans 1124×446 px of a 2464 px frame. Boxing it does not describe a
rail — it describes the region a rail crosses. Rails want segmentation or line detection.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

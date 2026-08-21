---
id: 41-rf-detr-detector
title: RF-DETR — A General Detector That Needs No Prompt and No Training
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: in_progress
depends_on: [02-model-manager, 35-model-licence-surfacing, 36-depth-foundation-model]
relates: [20-inference-overlay-render, 37-foundation-model-in-viewer, 42-foundation-boxes-everywhere]
source_files:
  - backend/app/ml/foundation/detect.py
  - backend/app/ml/foundation/registry.py
  - backend/app/ml/foundation/build.py
  - backend/app/ml/inference/payloads.py
  - backend/app/ml/registry.py
  - backend/app/api/v1/foundation.py
routes:
  - POST /api/v1/foundation/predict
models: []
test_files:
  - backend/tests/test_foundation_detect.py
  - backend/tests/test_foundation_api.py
  - backend/tests/test_registry.py
data_flow: greenfield
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [object-detection, rf-detr, foundation-model, coco, licensing, transformers]
path: Inference/Compare
integration_contracts:
  - consumer: 42-foundation-boxes-everywhere
    function: "source_boxes_payload / Box(x>=0, fits_within)"
    when: "a foundation detector's proposals are saved into a dataset"
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**RF-DETR returns boxes that can exceed the frame.** Measured on the COCO sample: a `couch` box at x=0.9 ran 1.5 px past the right edge on a 640x480 image. `Box` requires `x >= 0` and `fits_within(width, height)`, so saving such a proposal into a dataset raises `ValueError`. Harmless for display — the viewer clips — but doc 42 must clamp to the frame before writing, and clamping is right here rather than dropping: an object touching the edge is real."
  - "The score threshold defaults to 0.3 and is per-request. RF-DETR emits 300 queries per image and most are near-zero, so there is no useful \"unthresholded\" mode; the number is a display choice with no principled value."
  - "Only `nano` was exercised against real weights. `small` and `base` are catalogue entries with sizes read from the HuggingFace API, unverified by a run."
  - "COCO's 91 classes are the whole vocabulary. On a chessboard it answers `cake` (0.52) and on thermal IR `tv` (0.32) — reasonable nearest-neighbours for things COCO has no word for, and a reminder that a general detector is general only over its training distribution."
sister_projects: []
---

# 41 — RF-DETR

## Purpose

Give the app a **general object detector** — boxes on any image, with no prompt and no
training. Until now the only route to a box was to train a head, which means labelling data
first; backwards for a tool whose selling point is starting *from* proposals.

## Architecture

RF-DETR is a **DINOv2 backbone + a C2f projector + a shallow 2-layer deformable DETR
decoder**, 300 queries, `d_model` 256. It is self-contained, so it is a `FoundationModel`
(doc 36's contract) rather than a `HeadInstance` — `build_foundation` gains one case and
nothing else in the app learns a new concept.

That its backbone *is* a DINOv2 is the point rather than a coincidence: "freeze the
backbone, train what sits on top" — this project's founding rule — applies to it unchanged,
which is what makes doc 44's fine-tuning a continuation rather than an exception.

```
FoundationSpec(task="detection")  ──▶ build_foundation ──▶ RfDetrModel
                                                              │
        processor.post_process_object_detection(target_sizes) │  xyxy, source coords
                                          _as_xywh ───────────┤  xywh, this project's convention
                                 source_boxes_payload ────────┘
                                          │
                            the same Prediction a head produces
```

### Why this and not the alternatives

Four candidates were checked on 2026-08-20; the Wave 7.5 doc carries the full table.
`dgcnz/dinov2_vitdet_DINO_12ep` ships a bare detectron2 `.pth` — a pickle this project
refuses (doc 15) — with no `config.json`. `itsprakhar/Yolo-DinoV2` publishes **no weights**.
`Sompote/DINOV3-YOLOV12` and any Ultralytics YOLO are **AGPL-3.0**, which for an
installable app is a licensing decision belonging to Wave 8, not a technical choice made in
passing. RF-DETR is Apache-2.0, ungated, safetensors-only, and `RfDetrForObjectDetection` is
already in the installed transformers 5.15.

## Data Model

| id | size | licence |
|---|---|---|
| `rf-detr-nano` | 116 MB | Apache-2.0 |
| `rf-detr-small` | 123 MB | Apache-2.0 |
| `rf-detr-base` | 123 MB | Apache-2.0 |

`ModelFamily` gains `rf-detr`; the kind is the existing `detector`.

## Business Rules

1. **Corners become width and height, once.** The processor returns **xyxy**; the dataset
   store, the overlay renderer and `Prediction.boxes` all speak **xywh** from the top-left.
   `_as_xywh` is the only conversion, because a missed one reads a corner as a size and
   draws boxes that are *plausibly* wrong rather than obviously wrong.
2. **The payload is assembled by `source_boxes_payload`, not rebuilt.** Split out of
   `boxes_payload` so the head path and the foundation path share the invariants that
   matter: the three arrays are read **positionally**, a zero-area box is dropped from all
   three together, and the cap applies to all three together. A partial drop is a silent
   mislabel, not a crash.
3. **Class names are read off the checkpoint.** `id2label` carries COCO's 91 classes, so the
   viewer shows `cat`, not `class 17`. Wave 3 left the ImageNet classifier rendering
   `class 416` precisely because its names lived somewhere the loader never looked.
4. **A score threshold is required, not optional.** 300 queries per image, mostly near-zero.
5. **Weights are never auto-downloaded** — `is_installed` is checked before
   `from_pretrained`, which would otherwise reach the network.

## API

`POST /api/v1/foundation/predict` gains `score_threshold` (default 0.3). The handler asks
whether the model *takes* one via a single `isinstance` at the boundary — a capability
check, not an id→implementation map, which `build_foundation` remains the only one of.
A uniform signature would mean the depth model accepting an argument it ignores.

## Verified

Against real weights on 2026-08-20. Downloaded through the app's own admin endpoint —
**116 MB on disk against a 116 MB estimate** — and run on MPS:

| image | result |
|---|---|
| COCO val2017 sample | **cat 0.96, cat 0.91, remote 0.91, remote 0.88, couch 0.41** — correct, 62 ms |
| chess photograph | `cake` 0.52 over the whole board |
| thermal IR frame | `tv` 0.32 over the whole frame |

The first is the point: five correct detections with real class names and sensible boxes, no
prompt and no training. The other two are COCO's vocabulary reaching for its nearest word
for something it has no class for — worth recording so the limit is understood rather than
rediscovered.

First call 679 ms, subsequent calls **59–62 ms**: the per-id cache in `build_foundation` is
doing its job.

## Security

`foundation_id` is a registry key, never a path or repo id, so a traversal attempt fails at
the lookup. No new download path.

## Known Issues

See frontmatter — in particular the out-of-frame boxes, which doc 42 must handle.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

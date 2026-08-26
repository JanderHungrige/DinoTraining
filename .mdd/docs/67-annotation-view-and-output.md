---
id: 67-annotation-view-and-output
title: Show Masks, Boxes or Both — and Say What Gets Saved
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [22-mask-dataset-store, 28-mask-review-ui, 45-concept-segmentation-everywhere, 61-studio-mask-review]
relates: [20-overlay-registry, 42-foundation-boxes-everywhere, 66-prompted-detection-everywhere]
source_files:
  - backend/app/ml/foundation/concept.py
  - apps/frontend/src/types/annotationView.ts
  - apps/frontend/src/components/AnnotationViewToggle.tsx
  - apps/frontend/src/components/overlays/registry.tsx
  - apps/frontend/src/components/MaskReviewCanvas.tsx
  - apps/frontend/src/components/AnnotationCanvas.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
routes:
  - POST /api/v1/foundation/predict
models: []
test_files:
  - backend/tests/test_concept_foundation.py
  - apps/frontend/src/components/AnnotationViewToggle.test.tsx
  - apps/frontend/src/types/annotationView.test.ts
data_flow: reads-existing
last_synced: 2026-08-26
status: complete
phase: all
mdd_version: 11
tags: [overlays, masks, bounding-boxes, annotation-review, dataset-generator, annotation-studio, inference-viewer]
path: Annotation Studio/Review
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
---

# 67 — Show Masks, Boxes or Both

## Purpose

Reported as: *"if a model can produce boxes and segmentations there should be a question to
create boxes, segmentations, or both. Otherwise always indicate what type of annotations
will be created."*

Clarified in the same breath, and the clarification is the whole design: the ask is about
what is **shown**, not what is stored — *"just make the option to SHOW segmentation, bboxes
or both, and tell the user what will be the saved output for the different models."*

That split matters, because the storage question has a fixed answer and the display
question did not have one at all.

## Why storage is not a choice

A stored mask already exports as a box. `coco.py` writes each mask annotation with a
`bbox` derived from it (`rle_bbox`) and an `area` computed from it, so a segmented object
comes out of the exporter carrying both — **one** annotation, not two.

Storing a box *as well* would put the same object in the export twice, once in the box list
and once in the segmentation list, because the exporter emits the two tables separately on
the same image id. Anything trained on that file counts every segmented object twice. Doc
61 settled this — mask-only, box derived — and nothing here reopens it.

So the honest answer to "boxes, segmentations, or both?" is that **segmentation already
gives you both**, and the app should say so rather than offering a choice whose third
option corrupts the export.

## What is a choice

Which of the two you are looking at. Three surfaces render model output and each answered
this differently, none of them completely:

| surface | before |
|---|---|
| Annotation Studio | a `Show bounding boxes` checkbox, only when something was segmented — mask always on, so "boxes only" was unreachable |
| Dataset Generator | nothing. Masks, always |
| Inference Viewer | nothing. A `masks` prediction rendered the class map and no boxes existed to draw |

One control, one type, three surfaces:

```ts
export type AnnotationView = 'masks' | 'boxes' | 'both';
```

**Not a boolean.** The Studio's `showBoxes` was one, and a boolean can express "mask" and
"mask + box" but never "box alone" — which is the view someone wants when checking extents
against a detector, and the one state the old control could not reach.

**The options offered are derived from the prediction, not fixed.** A box-only model has no
masks to show, so it gets no toggle at all rather than a control with two dead options.
That check reads `render_hint`, never an id.

## The Inference Viewer needed a backend change

`_mask_payload` emitted `mask_png`, `class_stride`, `present_classes`, `height` and
`width` — and **no boxes**. The proposals it is built from carry a box each (doc 27 derives
it from the mask, tighter than the prompt's), so the information existed and was discarded
one function before the wire.

The payload now carries `boxes`, `scores` and `classes` alongside the class map, indexed
into the *same* `class_names` the map uses — so index 0 stays `background` and a phrase's
box and its mask region carry the identical index. Two indexing schemes for one prediction
is how a box ends up labelled with the previous phrase's name.

## Saying what will be saved

Independent of the view, and stated wherever a run is configured:

- a model whose `render_hint` is `masks` saves **segmentation masks**, and the COCO export
  carries a box derived from each
- a model whose `render_hint` is `boxes` saves **bounding boxes**

Derived from the catalogue entry, never from an id — the same rule doc 66 applied to
`takes_concept`, for the same reason: Grounded SAM, SAM 3 and a fine-tuned RF-DETR share no
id pattern, and the next model will share one with nothing.

The sentence is shown **before the run starts**, next to the model choice, because that is
when it can still change the decision.

## Tests

- the three views each render what they name, and `both` renders both
- a box-only prediction offers no toggle rather than dead options
- the view survives moving to the next image — it is a preference, not per-image state
- a mask payload carries boxes whose class indices agree with the class map's
- the saved-output line follows `render_hint` and is present for every model kind

## Known Issues

(none)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

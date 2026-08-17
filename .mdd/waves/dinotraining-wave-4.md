---
id: dinotraining-wave-4
title: "Wave 4: Dataset Generator (SAM + Expert-Head Auto-Annotation)"
initiative: dinotraining
initiative_version: 5
status: planned
depends_on: dinotraining-wave-3
demo_state: "User runs trained expert head(s) over new images, reviews/marks predictions, and saves a new dataset ready to train another head. Separately, SAM proposes segmentation masks over an image set which the user reviews and saves — closing the gap that made segmentation untrainable in-app."
created: 2026-08-14
hash: 06e8aaa4
---

# Wave 4: Dataset Generator (SAM + Expert-Head Auto-Annotation)

## Demo-State

In the **Dataset Generator** tab the user selects a backbone + one or more trained expert
heads and points them at a new image set. Predictions are shown with the same review UX as
the Annotation Studio (mark **positive / negative / unclear**, adjust or add boxes by hand),
and the reviewed results are saved back into the dataset store in the training format — ready
to train the next head. This closes the annotate→train→generate data flywheel.

This wave also brings **SAM (Segment Anything)** in as a second foundation annotator
alongside Grounding DINO: it proposes segmentation masks the user reviews and saves as
training targets. That is what finally makes the segmentation head trainable in-app —
until this wave lands, segmentation trains only on user-brought mask datasets.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | expert-annotator | — | planned | — |
| 2 | generator-review-ui | — | planned | — |
| 3 | active-learning-hints | — | planned | expert-annotator |
| 4 | generated-dataset-writer | — | planned | expert-annotator |
| 5 | sam-mask-annotator | — | planned | — |
| 6 | mask-review-ui | — | planned | sam-mask-annotator, generator-review-ui |

### Feature notes

- expert-annotator: reuse Wave 3 inference engine to propose boxes/labels from trained heads.
- generator-review-ui: reuse the Wave 1 annotation-canvas + counter (shared components).
- active-learning-hints (optional): surface low-confidence / disagreement items first.
- generated-dataset-writer: write reviewed results via the Wave 1 dataset-store, tagged with
  provenance (which head/version produced them).
- **Expert-head selection uses the same Wave 2 head-instance descriptor as Wave 3** — one
  shared head-picker contract across both tabs, listing task, provenance kind, datasets,
  classes and metrics. Review UX adapts to the head's render hint (box vs. mask review).
- **sam-mask-annotator:** SAM as a second foundation annotator beside Grounding DINO, managed
  by the same model manager (download, cache, remove). Supports the useful prompting modes —
  point/box prompt and automatic mask generation — and can take Grounding DINO boxes as its
  prompts, so an existing Wave 1 box dataset can be lifted into masks rather than
  re-annotated from scratch.
- **mask-review-ui:** mask equivalent of the Wave 1 box review — accept / reject / refine per
  mask, with the same pos/neg/unclear marking so the dataset store stays one format.
- **This wave is what makes segmentation trainable in-app.** Until it lands, the Wave 2
  segmentation head trains only on user-brought mask datasets and is otherwise used via its
  pretrained default. Depth stays inference-only unless a depth-target source is added later.
- Masks need an on-disk representation the Wave 1 dataset store does not have yet (RLE or
  polygon, plus a COCO-export story). Expect to extend `03-dataset-store` rather than fork it.

## Open Research

- Confidence/uncertainty signals worth surfacing for review prioritisation.
- Dataset versioning so generated data is traceable to the producing model.

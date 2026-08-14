---
id: dinotraining-wave-4
title: "Wave 4: Dataset Generator (Expert-Head Auto-Annotation)"
initiative: dinotraining
initiative_version: 1
status: planned
depends_on: dinotraining-wave-3
demo_state: "User runs trained expert head(s) over new images, reviews/marks predictions, and saves a new dataset ready to train another head."
created: 2026-08-14
hash: ef4d9dfb
---

# Wave 4: Dataset Generator (Expert-Head Auto-Annotation)

## Demo-State

In the **Dataset Generator** tab the user selects a backbone + one or more trained expert
heads and points them at a new image set. Predictions are shown with the same review UX as
the Annotation Studio (mark **positive / negative / unclear**, adjust or add boxes by hand),
and the reviewed results are saved back into the dataset store in the training format — ready
to train the next head. This closes the annotate→train→generate data flywheel.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | expert-annotator | — | planned | — |
| 2 | generator-review-ui | — | planned | — |
| 3 | active-learning-hints | — | planned | expert-annotator |
| 4 | generated-dataset-writer | — | planned | expert-annotator |

### Feature notes

- expert-annotator: reuse Wave 3 inference engine to propose boxes/labels from trained heads.
- generator-review-ui: reuse the Wave 1 annotation-canvas + counter (shared components).
- active-learning-hints (optional): surface low-confidence / disagreement items first.
- generated-dataset-writer: write reviewed results via the Wave 1 dataset-store, tagged with
  provenance (which head/version produced them).

## Open Research

- Confidence/uncertainty signals worth surfacing for review prioritisation.
- Dataset versioning so generated data is traceable to the producing model.

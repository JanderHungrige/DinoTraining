---
id: 25-expert-annotator
title: Expert Annotator — A Trained Head Proposes the Next Dataset
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [16-inference-engine, 18-multi-head-compose, 03-dataset-store]
relates: [12-head-instance-registry, 22-mask-dataset-store]
source_files:
  - backend/app/ml/annotators/expert.py
  - backend/app/ml/inference/results.py
  - backend/app/api/v1/generate.py
  - backend/app/api/v1/router.py
routes:
  - POST /api/v1/generate/expert
models: []
test_files:
  - backend/tests/test_expert_annotator.py
  - backend/tests/test_prediction_detections.py
  - backend/tests/inference_api_testkit.py
data_flow: reads-existing
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [auto-annotation, detection, flywheel, head-instance, provenance, dataset-generator]
path: Dataset Generator/Proposals
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The SUCCESS path has not been verified against real weights. No pretrained detection head exists to install — DINOv2 publishes linear heads for classification, segmentation and depth only, and the initiative records that detection stays train-your-own. All three real heads on this machine correctly return 409, so the refusal path IS verified end to end on MPS; the box-proposal path is covered only by a stubbed backbone. Verify it once a detection head has been trained through Wave 2, before trusting the generator on real data."
security_read_sites: []
---

# 25 — Expert Annotator

## Purpose

The flywheel's return leg: a head trained in Wave 2 runs over new images and proposes the
boxes that become the next dataset. This is the backend half — the review surface is
`26-generator-review-ui`.

## Why it is thin

Almost everything hard was built in Wave 3: resolving a head instance, checking it against
the backbone, sharing a backbone pass, and inverting predicted boxes back into the source
image's coordinates through the letterbox transform. This feature adds a proposal *shape*
on top and nothing else.

**No coordinate conversion happens here, and adding one would be a bug.**
`app/ml/inference/results.py` defines its box as xywh in absolute source pixels with a
top-left origin — the dataset store's exact convention — and doc 16 says it chose that
convention so this wave could consume it directly. The test asserting every proposed box
lies inside the source frame is what would catch a conversion creeping back in.

It runs through `run_heads` with a single head rather than the single-head path, so the
generator cannot drift from the viewer in how a head is prepared.

## Business Rules

- **Only a `boxes` render hint can be annotated.** A classification, segmentation or depth
  head is refused with a 409 naming what it *does* predict and where to run it instead.
  Returning an empty list would read as "found nothing", which is the opposite of what
  happened — and is the failure the user would waste the most time on.
- **Proposals are `positive`.** `unclear` would claim the model expressed doubt and
  `negative` would assert the object is absent; both are the reviewer's verdict to give.
  A detection *means* positive, and the reviewer demotes it.
- **Provenance is `expert-head`**, added to the vocabulary in `22-mask-dataset-store`.
- **The predicted class travels in `prompt`**, the same column a Grounding DINO proposal
  uses. One column, one meaning: "what this box was proposed as".
- **The response carries `head_name` *and* `head_summary`, never a filename** — the pair
  Wave 3's picker shows. `summary` says what the head does; `name` is what the user called
  it. Sending only one makes the same head read differently in two tabs.

## `Prediction.detections()`

A new sanctioned reader on the Wave 3 result type. The payload's `boxes`, `scores` and
`classes` arrays are read positionally and are only meaningful together — `boxes_payload`
drops a zero-area box from all three at once precisely to keep them aligned. Zipping them
in one place stops a consumer pairing box *i* with score *j*, which would produce a
plausible annotation carrying the wrong confidence and class.

Misaligned arrays return `[]` rather than a short zip: it means something other than
`boxes_payload` built the payload, and guessing an alignment silently mislabels.

## Error mapping

| Condition | Status |
|---|---|
| head does not produce boxes | **409** |
| head belongs to another backbone | **409** |
| backbone not installed | **409** |
| unknown head id | 404 |
| image missing | 404 |
| file is not an image | 415 |
| anything else raising `ValueError` | 422 backstop |

`HeadCannotAnnotateError` subclasses `ValueError`, so it is caught **before** the generic
clause or a 409 would be reported as a 422. `ModelNotInstalledError` subclasses
`LookupError` and is caught before it, or a 409 becomes a 404 — the ordering hazard
CLAUDE.md calls out.

## Testing note — a test that was wrong twice

The obvious test for thresholding is "a high threshold returns fewer boxes than a low one".
It failed about one run in five, and both causes were interesting:

1. The stub backbone draws **fresh random features per request**, so two calls are not
   comparable at all. Seeding fixed that and revealed the second problem.
2. The stub's random conv weights **saturate sigmoid**. Scores are
   `sigmoid(class) × sigmoid(centerness)`, and with random weights nearly every score lands
   above 0.99 — so even a 0.99 threshold filters nothing and the counts are equal on
   identical data.

Replaced with the property that is true regardless: **every returned box scores at or above
the requested threshold**, plus a seeded monotonicity check. A count comparison was testing
the fixture, not the feature.

## Dependencies

- `16-inference-engine` / `18-multi-head-compose` — resolution, preprocessing, the backbone
  pass and the geometry inversion.
- `03-dataset-store` — the `Box` type these proposals become.

## Known Issues

See frontmatter: the success path is stub-verified only, because no pretrained detection
head exists to install.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

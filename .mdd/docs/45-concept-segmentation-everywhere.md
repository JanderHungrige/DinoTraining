---
id: 45-concept-segmentation-everywhere
title: Concept Segmentation Everywhere — Grounded SAM Beyond the Generator
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: complete
depends_on: [23-mask-annotator-contract, 36-depth-foundation-model, 42-foundation-boxes-everywhere]
relates: [37-foundation-model-in-viewer, 41-rf-detr-detector, 20-overlay-registry]
source_files:
  - backend/app/ml/foundation/concept.py
  - backend/app/ml/foundation/registry.py
  - backend/app/ml/foundation/build.py
  - backend/app/ml/annotators/foundation.py
  - backend/app/api/v1/foundation.py
  - backend/app/api/v1/foundation_finetune.py
  - backend/app/api/v1/generate_foundation.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/foundation.ts
  - apps/frontend/src/components/FoundationPicker.tsx
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/components/HeadRunPanel.tsx
  - apps/frontend/src/hooks/useHeadRun.ts
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/styles.css
routes:
  - POST /api/v1/foundation/predict
  - POST /api/v1/generate/foundation
models: []
test_files:
  - backend/tests/test_concept_foundation.py
  - apps/frontend/src/components/FoundationPicker.concept.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [grounded-sam, sam3, concept-segmentation, foundation-model, inference-viewer, annotation-studio]
path: Inference Viewer/Foundation models
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**One concept field for all selected concept models in the viewer.** Two concept segmenters ticked at once share the string. Per-model concepts would need per-model state for a case nobody has asked for; the field says what it does."
  - "Grounding DINO re-segments phrases its own way. Asking for `chess piece. chess board.` came back as classes `chess board` and `chess` — phrase grounding splits and merges the prompt, and the class stored is whatever phrase actually matched. Not a bug here, but it means the class vocabulary of a concept-proposed dataset is not exactly what was typed."
  - "**13 seconds per image** for Grounded SAM on this machine (measured, 640x640, MPS). That is two models in sequence, and it is not the sub-second RF-DETR the Studio's other detectors are. There is no progress indication beyond the existing spinner."
  - "SAM 3 is registered and listed but was not exercised end-to-end here — only Grounded SAM was. Its `MaskAnnotator` is the one Wave 4 shipped and the wrapper is annotator-agnostic, but that is reasoning, not a measurement."
  - "Masks are composited **last-writer-wins** where two concepts overlap, matching a segmentation head's argmax. A pixel that is genuinely both is silently attributed to one."
sister_projects: []
---

# 45 — Concept Segmentation Everywhere

## Purpose

Make Grounded SAM and SAM 3 usable in the **Inference Viewer** and the **Annotation
Studio**, not only in the Dataset Generator.

## What this replaces

The wave planned a `general-detection-head` here: train `dense-detector` on COCO val2017 so
a general object-detection *head* would exist. Jan scrapped it on 2026-08-21, and the doc
that proposed it had already conceded the case — *"this will be modest… its value is that it
exists"*. Doc 44 then removed the last reason to want it: a fine-tuned RF-DETR reaches mAP
0.800 where the trained head reaches 0.587, so "a general detector" is a solved problem in
this app and a deliberately mediocre second one is not worth 5,000 images of training.

Making a model the user **already has installed** reachable from two more tabs is a better
use of the same slot.

## They were always foundation models

Grounded SAM was a `MaskAnnotator` (doc 23), reachable only from the Generator. But it is
self-contained, needs no trained head and no backbone to compose against — which is the
definition doc 36 wrote for a foundation model. It was in the wrong registry, not missing a
capability.

So `ConceptSegmenter` wears the foundation contract over the annotator that already exists.
No second implementation, no duplicated pipeline: `build_annotator` still constructs it, and
`propose` hands the raw `MaskProposal`s straight through.

## The two halves go to different places, on purpose

Grounding DINO finds boxes and SAM refines them into masks, so the pipeline produces both.

| surface | takes | why |
|---|---|---|
| Inference Viewer | **masks** | looking is the point there |
| Annotation Studio | **boxes** | that is what it reviews |

Taking the box back out is not throwing the segmentation away — it is using the *tighter*
extents SAM implies. The Studio gains a **text-prompted box proposer that beats Grounding
DINO alone**, which is the one thing doc 42's RF-DETR could not offer: naming something COCO
has never heard of.

Jan chose this over bringing mask review into the Studio. Wave 5 declined that deliberately —
the Studio's promise is hand-refinement and there is no mask editor — and that decision
stands untouched.

## Business Rules

1. **An empty concept returns an empty prediction, and is *refused* for proposals.** Two
   different answers to the same input, because the states differ: in the viewer an empty
   concept is "the user has not typed yet" and running a two-model pipeline over it costs
   13 seconds to produce nothing; in the Studio it would produce an empty canvas
   indistinguishable from "nothing found". The second needs a 409 that says so.
2. **Class 0 is background.** A phrase's mask index is its position **plus one**. Off by one
   paints every unmatched pixel as the first concept — a full-frame mask that reads as an
   over-eager model rather than an indexing bug.
3. **Install state is `all()` over the pipeline, and size is their sum.** A concept segmenter
   chains several checkpoints, so `model_id` answers neither question. Grounded SAM reports
   834 MB (Grounding DINO + SAM 2.1), not either half.
4. **The licence comes from the `AnnotatorSpec`, and `non_commercial` is `any()`.** A chain
   is only as permissive as its least permissive link.
5. **A concept segmenter cannot be fine-tuned.** `FinetunePanel` still filters on
   `render_hint === 'boxes'`, so it is excluded without a new rule.

## `proposesBoxes`, and why `render_hint` stopped being enough

Doc 42 filtered the pickers on `render_hint === 'boxes'`. A concept segmenter reports
`masks` — correctly; that is what the viewer draws — but its boxes are reviewable. The rule
became `render_hint === 'boxes' || takes_concept`, exported **once** from `foundation.ts` so
the Studio's filter and the picker's filter cannot drift apart. Depth is still refused, and
a test pins that the rule widened rather than dissolved.

## Verified

Against real weights through the real API on 2026-08-21, on a 640x640 chessboard photo:

```
POST /foundation/predict   grounded-sam  "chess piece. chess board."
  -> render_hint=masks  class_names=['background','chess board']  13.4 s

POST /generate/foundation  grounded-sam  same concept, threshold 0.25
  -> chess board 0.55 (0,0,640,640)   provenance=foundation-model
     chess       0.26 (0,0,640,343)   provenance=foundation-model

POST /generate/foundation  grounded-sam  no concept
  -> 409 "Grounded SAM (Grounding DINO + SAM 2.1) needs a concept — type what
          you are looking for."
```

**Verified in the running app on 2026-08-21.** Grounded SAM and SAM 3 appear in the Studio's
detector list and in the viewer's foundation list; the concept field is absent for RF-DETR,
appears when Grounded SAM is selected, and in the viewer appears only once a concept model is
actually ticked.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

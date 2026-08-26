---
id: 66-prompted-detection-everywhere
title: Prompted Detection Everywhere — Grounding DINO as a Foundation Model
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [04-grounding-dino-annotator, 42-foundation-boxes-everywhere, 45-concept-segmentation-everywhere]
relates: [27-grounded-sam-annotator, 41-rf-detr-foundation, 65-starter-set]
source_files:
  - backend/app/ml/foundation/registry.py
  - backend/app/ml/foundation/prompt_detect.py
  - backend/app/ml/foundation/build.py
  - backend/app/api/v1/foundation.py
  - apps/frontend/src/components/FoundationPicker.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/lib/generatorProposal.ts
routes:
  - GET /api/v1/foundation
  - POST /api/v1/generate/foundation
  - POST /api/v1/inference/compose
models: [grounding-dino-tiny, grounding-dino-base]
test_files:
  - backend/tests/test_prompt_detect.py
  - backend/tests/test_foundation_api.py
  - apps/frontend/src/components/FoundationPicker.test.tsx
data_flow: reads-existing
last_synced: 2026-08-26
status: complete
phase: all
mdd_version: 11
tags: [grounding-dino, foundation-model, prompted-detection, inference-viewer, dataset-generator, open-vocabulary]
path: Inference Viewer/Foundation Models
integration_contracts:
  - function: build_foundation(foundation_id)
    when: any code turning a foundation id into a running model
    note: the one sanctioned dispatch point; an `if foundation_id == …` elsewhere is a defect
satisfies_contracts: []
known_issues: []
security_read_sites: []
---

# 66 — Prompted Detection Everywhere

## Purpose

Reported as: *"Grounding DINO is not available in the Inference Viewer or the Dataset
Generator?"* Correct, and it had been the odd one out for two waves.

The Annotation Studio has offered it since Wave 1 as its own mode. Doc 42 then made
self-contained detectors runnable everywhere, and doc 45 did the same for the two *mask*
annotators — Grounded SAM and SAM 3 — by registering them as foundation models. Grounding
DINO fell between the two: it is not a plain detector, because it needs a text prompt, and
it is not a mask annotator, because it returns boxes. So the one model the Studio was built
around was the only one the other two tabs could not run.

## The shape of the gap

There were **three** kinds of foundation model and this is a fourth:

| | prompt? | output | implementation |
|---|---|---|---|
| RF-DETR | no | boxes | `RfDetrModel` |
| Depth Anything | no | depth map | `DepthAnythingModel` |
| Grounded SAM, SAM 3 | yes | masks | `ConceptSegmenter` |
| **Grounding DINO** | **yes** | **boxes** | **`PromptedDetector`** |

The two axes are independent, and the code had them fused: `FoundationSpec.takes_concept`
was defined as `annotator_id is not None`, so "needs a prompt" was inferred from "is a mask
pipeline". That is the same defect as reading a head's capability off its `task` label — it
works until something is the other combination, and this is that something. `takes_concept`
is now its own field.

## What it reuses

Nothing here is a second Grounding DINO. `detector.py` has owned prompting, the box
threshold and the model's xyxy → the store's xywh since Wave 1, and `PromptedDetector` is
that behind the foundation contract, exactly as `ConceptSegmenter` is `build_annotator`
behind the same contract.

**Classes are the matched phrases.** Grounding DINO returns a phrase per box, not a class
index, so the phrases are collected in first-appearance order and each box carries its
index — the same mapping `_mask_payload` makes for the segmenter, minus the background
class, because a box payload has no background. A phrase therefore keeps one colour across
the boxes it matched.

**Both sizes, matching doc 27's tiers.** `grounding-dino-tiny` is in the starter set;
`grounding-dino-base` is the better-recall option and appears once installed.

## Why this and not a fourth Generator mode

The Dataset Generator could have grown a "prompt" radio mirroring the Studio's. That fixes
one tab. Registering Grounding DINO in the foundation catalogue fixes three at once —
Inference Viewer, Studio and Generator — because all three already read that catalogue and
all three already understand `takes_concept`. Doc 45 made exactly this trade and it is the
reason this change is a catalogue row plus one class rather than a UI feature repeated per
tab.

The one place the frontend was not ready: the Generator's `FoundationPicker` was mounted
without an `onConceptChange`, so a prompted detector would have been selectable with
nowhere to type the prompt. `FoundationConfig` now carries a concept, and the picker shows
the field when the selected model asks for one — which is the behaviour the Studio already
had.

## An empty prompt is not an error

It is the state before the user has typed. `ConceptSegmenter` already answers an empty
concept with an empty prediction rather than running a model over nothing, and this does
the same. Running Grounding DINO on `""` matches everything weakly and returns noise that
looks like a working detector having a bad day.

## Tests

- a prompted detector reports `takes_concept` while returning `boxes` — the combination the
  old derived property could not express
- the phrase→index mapping keeps one index per phrase, and boxes carry it
- an empty concept returns an empty prediction and loads no model
- both catalogue sizes resolve, and each loads the weights its own row names
- the Generator shows a prompt field for a prompted detector and none for RF-DETR

## Known Issues

(none)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

---
id: 27-grounded-sam-annotator
title: Grounded SAM — Text-Prompted Masks Without a Gated Model
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [23-mask-annotator-registry, 22-mask-dataset-store, 04-grounding-dino-annotator]
relates: [25-expert-annotator, 02-model-manager, 65-starter-set]
source_files:
  - backend/app/ml/segmenter.py
  - backend/app/ml/registry.py
  - backend/app/ml/annotators/grounded_sam.py
  - backend/app/ml/annotators/registry.py
  - backend/app/ml/annotators/build.py
  - backend/app/ml/foundation/registry.py
  - backend/app/api/v1/generate.py
  - backend/app/api/v1/annotators.py
  - apps/frontend/src/api/annotators.ts
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/components/MaskSourceFields.tsx
routes:
  - POST /api/v1/generate/masks
models: []
test_files:
  - backend/tests/test_grounded_sam.py
  - backend/tests/test_generate_masks_api.py
  - backend/tests/test_annotator_registry.py
  - apps/frontend/src/components/GeneratorSetup.annotator.test.tsx
data_flow: reads-existing
last_synced: 2026-08-26
status: complete
phase: all
mdd_version: 11
tags: [grounded-sam, sam2, grounding-dino, segmentation, coco-rle, mask-annotator, model-variants]
path: Dataset Generator/Proposals
integration_contracts:
  - function: build_annotator(annotator_id)
    when: any code turning an annotator id into a running annotator
    note: the one sanctioned dispatch point; an `if annotator_id == …` elsewhere is a defect
satisfies_contracts: []
known_issues:
  - "transformers warns on every load that the checkpoint is a `sam2_video` config being instantiated as `Sam2Model`. The repo serves both image and video use and Sam2Model is the image half; verified against the real weights that masks are exact. Cosmetic, but it appears in the server log at every start."
security_read_sites: []
---

# 27 — Grounded SAM

## Purpose

The ungated implementation of the `MaskAnnotator` contract, and the feature that makes the
whole wave verifiable. A text concept goes to Grounding DINO, its boxes become SAM 2.1 box
prompts, and the masks come back with their originating boxes — reproducing SAM 3's contract
(concept in, masks **and** boxes out) under Apache-2.0, with no account, no token and no
access request.

## Measured before it was written

Two things about SAM 2's transformers API are not guessable and both fail *silently*. Both
were probed against the real checkpoint first.

**Batching.** `input_boxes` takes one inner list per image with every box inside it:
`[[b1, b2]]` returns `(2, 1, H, W)` — one mask per box. Nesting it wrong returns one mask
for many boxes, which looks like a working feature that quietly ignores most of the input.

**Device.** Masks come back on the model's device, and this project runs on MPS:

```
--- mps ---
direct .numpy() FAILED -> TypeError: can't convert mps:0 device type tensor to numpy
detach().cpu().numpy() OK
```

That is bug class #1 verbatim — the one that let 668 tests pass in Wave 3 while every dense
prediction 500'd, because every test builds CPU tensors. `segmenter.py` routes every
conversion through a single `_to_numpy`, and the module docstring records why.

## Architecture

```
detector.py    Grounding DINO — prompting, and the model's xyxy → the store's xywh
segmenter.py   SAM 2.1 — box prompts → masks, and the one device→host hop
annotators/grounded_sam.py   the join
annotators/build.py          id → implementation, the only dispatch point
```

Neither stage is re-implemented. `segmenter.py` mirrors `detector.py` exactly — cached per
`(model_id, device)`, never downloads, `ModelNotInstalledError` when absent — because a
second loading convention is how two models end up with different cache lifetimes.

### The one conversion

`detector.py` converts the model's xyxy into the store's xywh **once**, so nothing
downstream has to guess. SAM wants xyxy back, and `_to_xyxy` is the mirror of that
conversion and the only place it happens. Doing it anywhere else would give two conventions
sharing variable names.

### Zipping masks back to boxes

Masks, IoU scores and detections are positional and must stay aligned. Dropping an empty
mask **drops its box and score with it** — a partial drop attributes every later mask to the
wrong detection, and the result looks entirely plausible. If SAM returns fewer masks than
prompts (it did not in testing, but the shape is not contractual) the loop stops rather than
pairing the remaining boxes with nothing.

The stored score is `detection.score × iou`: the first is how well the *concept* matched,
the second is SAM's confidence in the *mask*. Multiplying stops a confident box with a poor
mask outranking both.

The concept recorded per mask is the **phrase Grounding DINO matched**, not the whole
prompt — `"a cat. a dog."` produces per-box phrases, and that is what a reviewer needs
beside each mask.

## API

### `POST /api/v1/generate/masks`

`{image_path, concept, annotator_id?, threshold?}` → masks, each carrying:

- **`rle`** — what gets stored. COCO uncompressed RLE, already the wire format, and
  submittable to `PUT /datasets/{id}/images/masks` unchanged. A test performs exactly that
  round trip, because "the proposal is storable" is the contract that matters.
- **`x,y,w,h`** — derived server-side from the mask, so no client decodes an RLE to place an
  overlay. Note this is the *mask's* box, not the prompt's: SAM often tightens a loose box.
- **`mask_png`** — preview only, base64, per the Wave 3 rule. ~1 KB against 307 KB dense.

| Condition | Status |
|---|---|
| unknown annotator id | 404 |
| catalogued but not implemented (SAM 3 today) | **501** |
| a required model not downloaded | **409**, naming what to download |
| image missing / not an image | 404 / 415 |
| empty concept | 422 |

**501 rather than 404 for SAM 3**: the id is real and listed in the admin tab, so "not
found" would send the user hunting for a typo. The message points at Grounded SAM, which
does the same job today.

## Verified end to end

Against the real installed weights on MPS, prompt `"a red circle. a blue square."` over a
640×480 scene:

| concept | mask area | true area | error |
|---|---|---|---|
| a red circle | 31,417 px | π·100² = 31,416 | **1 px** |
| a blue square | 32,197 px | 180² = 32,400 | 0.6% |

403 and 381 RLE runs for a 307,200-pixel frame. Both stages ran on MPS without a single
device error — the `_to_numpy` discipline holding is the point of that observation.

This is the first Wave 4 feature whose success path is verified against real weights rather
than a stub; docs 25 and 26 could not be, because no pretrained detection head exists.

## The three sizes

Both stages are swappable and always were: `GroundedSamAnnotator.__init__` takes a
`detector_id` and a `segmenter_id`, and both loaders cache per `(model_id, device)` so two
sizes can be live at once. Until 2026-08-26 nothing passed either, so the capability existed
and was unreachable.

**Exposed as three named tiers, not as a 2x3 matrix.**

| id | detector | segmenter | download | what it buys |
|---|---|---|---|---|
| `grounded-sam` | grounding-dino-tiny | sam2.1-hiera-small | 834 MB | the starter set; fast |
| `grounded-sam-base` | grounding-dino-base | sam2.1-hiera-base-plus | 1,199 MB | finds more of what you asked for |
| `grounded-sam-large` | grounding-dino-base | sam2.1-hiera-large | 1,747 MB | the same recall, tighter mask edges |

Two facts set that table's shape. **There is no larger Grounding DINO** — IDEA-Research
published tiny and base as open weights, and 1.5 / Pro are API-only — so `-large` differs
from `-base` on the SAM half alone, and the detector column stops at two. And the two halves
answer different questions: Grounding DINO decides *what is found*, SAM decides *how well it
is outlined*. SAM cannot outline what the detector missed, which is why recall is the first
thing to spend a gigabyte on and edge quality the second.

The dominated combinations are omitted rather than hidden. `tiny + large` is the defensible
one of them — crisp edges on a smaller set of found objects — and anyone who wants it can
say so; it is one registry row, not a redesign.

### Why a variant is a registry row

`build_annotator` maps an id to an implementation and takes no arguments, so the id is the
only selector. That is the constraint, and it is the right one: **readiness is a property of
a set of models**, and a row is what makes "is this ready to run?" answerable. Its builders
now receive the `AnnotatorSpec` and read the model ids off it, so the pipeline can only ever
load what the readiness check tested — a builder holding its own model ids would let Admin
report ready while the annotator loaded something else.

### Provenance stays `grounded-sam` for all three

It names the **pipeline, not the size**. `datasets/schema.py` holds the provenance enum in a
SQLite CHECK constraint, so a value per variant would need a migration on every future size —
and the question provenance exists to answer is "which masks came from the ungated path",
which all three answer the same way. Which tier produced a mask is a run-time choice, not a
property of the annotation.

### The prompt style is data, not an id comparison

`GeneratorSetup` decided its prompt hint with `annotatorId === GROUNDED_SAM`, which is the
exact defect doc 23 names — and it fails in the quiet direction: a new variant would have
silently shown SAM 3's single-concept wording while accepting multi-phrase prompts. The
trait is now `prompt_style` on the spec (`phrases` for the Grounded SAM tiers, `concept` for
SAM 3), carried in the `/annotators` payload.

## Dependencies

- `23-mask-annotator-registry` — the contract, the catalogue and `MaskProposal`.
- `22-mask-dataset-store` — `rle_encode`/`rle_bbox`, and the `grounded-sam` provenance.
- `04-grounding-dino-annotator` — the detector, its prompt normalisation and its conversion.

## Known Issues

See frontmatter: a cosmetic `sam2_video` config warning on every model load.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

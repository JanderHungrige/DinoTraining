---
id: 30-sam3-annotator
title: SAM 3 Annotator — Concept-Prompted Masks, User-Downloaded
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [23-mask-annotator-registry, 27-grounded-sam-annotator, 24-hf-token-settings]
relates: [02-model-manager]
source_files:
  - backend/app/ml/annotators/sam3.py
  - backend/app/ml/annotators/build.py
  - backend/app/ml/segmenter.py
  - backend/app/ml/downloads.py
  - apps/frontend/src/components/GeneratorSetup.tsx
routes: []
models: []
test_files:
  - backend/tests/test_sam3_annotator.py
  - backend/tests/test_download_patterns.py
  - backend/tests/test_registry.py
  - apps/frontend/src/components/GeneratorSetup.test.tsx
  - apps/frontend/src/components/GeneratorSetup.annotator.test.tsx
data_flow: reads-existing
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [sam3, gated-models, concept-prompt, mask-annotator, licensing]
path: Dataset Generator/Proposals
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "SAM 3 takes ONE concept per call. A multi-phrase prompt like 'a red circle. a blue square.' is read as a single long concept: verified against real weights it returned one mask at score 0.372, against 0.977 and 0.968 when the same two phrases were run separately. Grounded SAM handles the joined form correctly because Grounding DINO reports which phrase matched each box. The generator's concept field now shows different placeholder and guidance per annotator, but the prompt is NOT split automatically — running one concept at a time is the user's job. Splitting a multi-phrase prompt and calling SAM 3 once per phrase would make the two annotators behave identically and is the obvious next improvement."
security_read_sites: []
---

# 30 — SAM 3 Annotator

## Purpose

The gated implementation of the mask-annotator contract. SAM 3 is *concept-prompted*: a
text noun phrase goes straight in and masks come straight out, with **no detector stage**.
That is the whole difference from Grounded SAM, which composes two models to reach the same
contract — and it is why both satisfy one interface rather than the caller knowing which it
has.

## Verified against real weights — 2026-08-19

Meta granted access, the 3.2 GB download completed, and Phase 7b ran. **No code changed** —
the API shape introspected from `transformers` 5.15 was correct, the singleton-axis squeeze
was a harmless no-op, and `_to_numpy` carried the mask tensors off MPS without complaint.

All four risks the stub could not cover came back clean: mask shape, device hop, positional
score alignment, and `target_sizes` order on a non-square image (every proposal decoded at
640x480 with run lengths summing exactly to the frame).

Accuracy on a synthetic scene:

| concept | score | mask area | true area | error |
|---|---|---|---|---|
| `a red circle` | **0.977** | 31,434 | π·100² = 31,416 | 0.06% |
| `a blue square` | **0.968** | 32,250 | 180² = 32,400 | 0.5% |
| `circle` | 0.974 | 31,539 | — | bare noun works |
| `a unicorn` | — | *nothing* | — | does not hallucinate |

SAM 3 scores noticeably higher than Grounded SAM on the same image (0.977 against 0.883),
which is the quality difference the licence buys.

## What the API shape is based on

Not guesswork — introspected from the installed `transformers` 5.15:

```
Sam3Processor.__call__(images=…, text=…, return_tensors="pt")
Sam3Model.forward(pixel_values, input_ids, attention_mask, …) -> Sam3ImageSegmentationOutput
Sam3Processor.post_process_instance_segmentation(outputs, threshold, mask_threshold, target_sizes)
    -> list[dict] with:
         scores  (num_instances,)
         boxes   (num_instances, 4) xyxy
         masks   (num_instances, height, width) binary
```

The library's own docstring carries a worked example, which made this stronger than a
guess — and the Phase 7b run above confirmed every part of it. No code changed as a result.

## Nothing here downloads anything

`facebook/sam3` is 3.2 GB behind Meta's manual approval. The user triggers the download
from the admin tab, exactly as for every other model. `load_segmenter` raises
`ModelNotInstalledError` when the weights are absent, and asking for SAM 3 without them is
a **409 pointing at the admin tab** — not a 501, which would mean "not implemented", and
not a silent 3.2 GB fetch.

This is now pinned by tests rather than convention:

- `snapshot_download(` appears in exactly one file, `app/ml/downloads.py`
- every loader — detector, segmenter (both families), backbone — refuses a missing model
- the catalogue total is bounded, so a mis-typed size cannot claim 30 MB or 30 GB

The whole catalogue is **7.9 GB** if a user downloads everything; the installer ships
**0 MB** of weights.

## The loader dispatches on family

`segmenter.py` now picks its processor/model classes from a table keyed by family rather
than branching on `sam3`. Loading is the same job either way — resolve a directory, refuse
to download, move to the device, `eval()`. How a model is *prompted* is its annotator's
business, and that is where the two diverge.

## A 403 with a valid token

The most confusing failure this app can produce, and the one the wave doc called out. Meta
grants SAM 3 access by hand, so a user can hold a perfectly good token and still be
refused. Telling them to check it is advice they have already followed.

`failure_message` therefore produces three different answers:

| situation | message |
|---|---|
| 403, needs approval (SAM 3) | "Access has not been granted yet… granted by a person, not automatically" |
| 403, terms only (DINOv3) | "Accept the licence on the model page, and check the token" |
| anything else | exception class + repo, never the exception text |

The last row is not cosmetic: HuggingFace errors embed the request URL, and **a token can
ride along in it**. A test asserts no failure message ever contains the token.

## The UI offers it only once installed

The annotator picker in the generator lists annotators whose models are actually
downloaded, so SAM 3 appears the moment it is installed and not before — and the picker
hides itself entirely while only one annotator is ready, which is the state of a fresh
install. The admin tab is where a user goes to get it, with its licence, its size and its
manual-approval notice already on the card from `23-mask-annotator-registry` and
`24-hf-token-settings`.

## Differences from Grounded SAM worth knowing

- **One concept per call, and it matters more than it sounds.** Grounding DINO reports
  which phrase matched each box, so Grounded SAM handles `"a cat. a dog."` natively. Given
  the same string SAM 3 reads it as one long concept: measured, **one mask at score 0.372**
  against **0.977 and 0.968** for the phrases run separately. The generator's concept field
  therefore shows a different placeholder and hint per annotator.
- **Score is the model's own.** Grounded SAM multiplies the detector's concept match by
  SAM's mask IoU because it has two numbers; SAM 3 has one.
- **No box conversion.** There is no detector stage, so the xywh↔xyxy round trip that
  `grounded_sam._to_xyxy` performs does not arise.

## Known Issues

See frontmatter: SAM 3 takes one concept per call, and a multi-phrase prompt degrades badly.
The UI now warns per annotator; splitting the prompt automatically is the next improvement.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

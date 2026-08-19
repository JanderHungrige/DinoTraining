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
data_flow: reads-existing
last_synced: 2026-08-19
status: in_progress
phase: integration-pending
mdd_version: 11
tags: [sam3, gated-models, concept-prompt, mask-annotator, licensing]
path: Dataset Generator/Proposals
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "NOT VERIFIED AGAINST REAL WEIGHTS. facebook/sam3 needs Meta's manual approval and is 3.2 GB, which is the user's download to make. The API shape is taken from the installed transformers 5.15 (Sam3Processor(images=, text=) and post_process_instance_segmentation returning scores/boxes/masks) and the pipeline is covered by stubbed tests. What a stub cannot prove is exactly what SAM 2 taught in doc 27: the true output shapes, and whether mask tensors arrive on the model's device. _to_numpy covers the second; the first needs one real run. Resume at Phase 7b when access is granted — no re-implementation should be needed."
security_read_sites: []
---

# 30 — SAM 3 Annotator

## Purpose

The gated implementation of the mask-annotator contract. SAM 3 is *concept-prompted*: a
text noun phrase goes straight in and masks come straight out, with **no detector stage**.
That is the whole difference from Grounded SAM, which composes two models to reach the same
contract — and it is why both satisfy one interface rather than the caller knowing which it
has.

## Status: written, stubbed, not yet run

This feature is deliberately marked `in_progress` / `integration-pending` rather than
complete. Everything is implemented and covered by tests, and one thing is missing: a run
against the real checkpoint.

Doc 27 is why that distinction matters. SAM 2 taught two lessons a stub cannot teach —
the exact batching shape, and that mask tensors come back on the model's device where
`.numpy()` raises. Both were found by *measuring the real model before writing the code*.
For SAM 3 that was not possible: the repo is gated behind manual approval. Claiming
"complete" would be claiming a verification that has not happened.

**Resume at Phase 7b when access is granted.** No re-implementation is expected.

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

The library's own docstring carries a worked example, which is what makes this stronger
than a guess — but it is still not a run.

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

- **One concept per call.** Grounding DINO reports which phrase matched each box, so
  Grounded SAM can store a per-mask concept from a prompt like `"a cat. a dog."`. SAM 3
  takes one concept, so every mask in a call carries it.
- **Score is the model's own.** Grounded SAM multiplies the detector's concept match by
  SAM's mask IoU because it has two numbers; SAM 3 has one.
- **No box conversion.** There is no detector stage, so the xywh↔xyxy round trip that
  `grounded_sam._to_xyxy` performs does not arise.

## Known Issues

See frontmatter: not verified against real weights.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

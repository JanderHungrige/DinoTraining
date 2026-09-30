---
id: 96-sam3-finetune
title: SAM 3 Fine-Tuning — Phrases and Outlines, Trained on a 16 GB Mac
edition: DinoTraining
depends_on: [30-sam3-annotator, 92-data-requirements-contract, 93-finetune-framework, 94-sam2-finetune]
relates: [97-finetune-ui, 98-finetune-for-agents]
source_files:
  - backend/app/finetune/adapters/sam3.py
  - backend/app/finetune/adapters/__init__.py
  - backend/app/finetune/adapter.py
  - backend/app/finetune/adapters/sam2.py
  - backend/app/finetune/adapters/rfdetr.py
  - backend/app/finetune/runner.py
  - backend/app/finetune/requirements.py
  - backend/app/ml/segmenter.py
  - backend/app/ml/foundation/build.py
  - backend/app/ml/foundation/concept.py
  - backend/app/api/v1/foundation.py
routes:
  - POST /api/v1/finetune/jobs (finetune_id sam3)
  - GET /api/v1/foundation (fine-tuned SAM 3 listed as "SAM 3 · <name>")
models:
  - FoundationInstance weights_kind "sam3-decoders" (sam3_decoders.pt)
test_files:
  - backend/tests/test_finetune_sam3.py
  - backend/tests/test_finetune_runner.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [fine-tuning, sam3, concept-segmentation, hungarian-matching, memory, mps]
path: Training/Fine-tuning/SAM 3
initiative: dinotraining
wave: dinotraining-wave-12
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "No full SAM 3 run has completed on real weights yet, and a saved SAM 3 fine-tune has not been loaded (see What is verified). The code path mirrors SAM 2's, which is verified end to end."
  - "Slow on a 16 GB M1: the frozen encoder costs ~6 s per picture and only ~24 pictures' features fit the memory budget, so later rounds recompute the rest. A GPU machine (Wave 13's remote runner) is the comfortable place for it."
  - "Licence terms for fine-tuned SAM 3 derivatives are still to be read (wave research item)."
  - "Only one learning-rate and loss weighting (DETR's) was tried."
security_read_sites: []
sister_projects: []
---

# 96 — SAM 3 Fine-Tuning

## Purpose

The wave asked for SAM 3 to fine-tune, or to state precisely why it cannot on this
machine. A spike settled it first: **it can**, and this doc records both the adapter and
what running it on a 16 GB Mac taught.

## Feasibility, measured (2026-09-30, M1, 16 GB)

**Model:**
- 840 M parameters, 3.4 GB on the GPU.
- Training only the DETR decoder, the mask decoder and the scoring head is **15 M
  parameters**.

**One step, timed with `torch.mps.synchronize()`:**

| Part | Time | Cacheable |
|---|---|---|
| frozen image encoder | 6.2–6.6 s per picture | yes (features: 113 MB fp32, 56 MB fp16) |
| trainable forward + backward | ~1.1 s after warm-up | — |

The first, unsynchronised timings (26–63 s per step) were MPS's asynchrony, not the
cost.

## How (`adapters/sam3.py`)

- **What is cached:**
  - the frozen encoders' features, per picture, fp16, within a **memory budget**;
  - the position encodings, once (every picture is resized to 1008 px);
  - each class phrase, encoded once.
- **Training, per picture and phrase:**
  - Hungarian matching of the 200 queries to the phrase's objects, on mask dice, box L1
    and score;
  - then focal loss on the query scores, the phrase-presence loss, L1 + GIoU on matched
    boxes, and dice + focal on matched masks (DETR's weights).
  - A picture without the phrase teaches "none here".
- **Score:** matched mIoU. Predicted and true objects are paired one-to-one, and a missed
  or invented object counts 0.
- **Saved:** the trained parts only, `sam3_decoders.pt` (~60 MB), loaded over the base
  model by `load_segmenter`. Listed as **"SAM 3 · <name>"** and prompted by a concept like
  the catalogue SAM 3.

## Found live: a fixed cache budget swapped the machine

**The first run:**
- **Setup:** a 3 GB feature cache next to the 3.4 GB model, with the app and the rest of
  the machine alongside.
- **Result:** the Mac went to **24.5 of 25.6 GB of swap**, and the first epoch did not
  finish in 25 minutes. Cancelling did not help either, because the runner only checked
  between epochs.

**Two fixes, for every adapter:**
- **Budgets are a share of physical memory** (`memory_budget`): 8 % for SAM 3 (1.37 GB here,
  ~24 pictures) and 15 % for SAM 2.
- **Cancel is checked between pictures** (`FinetuneData.stop`). A test pins a cancel that
  lands mid-epoch.

## What is verified, and what is not

**Verified:**
- **The spike:** real training steps on the installed weights, with the timings and
  memory above. The loss is computed through the Hungarian match and backpropagated into
  the 15 M trained parameters.
- **Base score on the filled-ring test pictures:** matched mIoU **0.434**, measured by the
  adapter inside the runner twice, identically. SAM 3 finds the rings but outlines them
  without the hole the convention includes, and misses or adds objects.
- **Unit tests:** matching (missed and invented objects count 0), the loss preferring the
  query that found the object, "none here" for a picture without the phrase, and the
  adapter's registration.
- **Cancelling inside an epoch** worked live: 45 s from cancel to "cancelled", including a
  base-model evaluation that now also checks the flag.

**Not verified: a full run to completion, and loading a saved SAM 3 fine-tune.**
- **Why:** the second attempt ran while another project's vision process (NinaNatur,
  19 GB) held most of this Mac's memory. The system swapped about 2.8 GB every 10 s, and
  the run was cancelled rather than slow both jobs down further.
- **Expected cost on a free 16 GB M1:** about 6 min for the first round on 49 pictures,
  then about 3 min per round.
- **What remains:** the first complete run, the before/after, and the "SAM 3 · <name>"
  listing and load belong here once done.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

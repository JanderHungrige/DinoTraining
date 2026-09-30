---
id: 94-sam2-finetune
title: SAM 2 Fine-Tuning — The Mask Decoder on Your Own Outlines
edition: DinoTraining
depends_on: [27-grounded-sam, 61-studio-masks, 92-data-requirements-contract, 93-finetune-framework]
relates: [85-model-input-planning, 96-sam3-finetune, 97-finetune-ui]
source_files:
  - backend/app/finetune/adapters/sam2.py
  - backend/app/finetune/adapters/__init__.py
  - backend/app/finetune/requirements.py
  - backend/app/finetune/runner.py
  - backend/app/api/v1/finetune_jobs.py
  - backend/app/ml/segmenter.py
  - backend/app/ml/foundation/registry.py
  - backend/app/ml/foundation/build.py
  - backend/app/ml/foundation/concept.py
  - backend/app/api/v1/foundation.py
routes:
  - POST /api/v1/finetune/jobs (finetune_id sam2.1-hiera-small)
  - GET /api/v1/foundation (fine-tuned SAMs listed as "Grounded SAM · <name>")
models:
  - FoundationInstance weights_kind "sam-mask-decoder" (mask_decoder.pt)
test_files:
  - backend/tests/test_finetune_sam2.py
  - backend/tests/test_finetune_runner.py
data_flow: writes-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [fine-tuning, sam2, segmentation, masks, grounded-sam, mps]
path: Training/Fine-tuning/SAM 2
initiative: dinotraining
wave: dinotraining-wave-12
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Only SAM 2.1 small has a requirements entry. Base-plus and large use the same adapter; their entries (and memory figures) are not added yet."
  - "Verified on synthetic outlines only: the app holds no real instance-mask dataset of useful size. Real masks come from the Studio or the Generator (Grounded SAM, corrected), and the first real run should be recorded here."
  - "A fine-tuned SAM runs behind Grounding DINO tiny (the fast tier). Pairing it with the base Grounding DINO tier is not offered yet."
security_read_sites: []
sister_projects: []
---

# 94 — SAM 2 Fine-Tuning

## Purpose

SAM outlines almost anything from a box, so what fine-tuning can teach it is **your
outlines**: where the edge of your objects is, and your annotation conventions. This
trains SAM 2.1's mask decoder on the user's own masks and makes the result usable wherever
Grounded SAM is.

## How (`adapters/sam2.py`)

- **Frozen encoder, cached.** Each picture's image embeddings are computed once by the
  frozen encoder. They are kept on the CPU in fp16 up to 3 GB; the rest are recomputed.
- **Only the mask decoder trains.** Saved as `mask_decoder.pt`, a few MB instead of the
  whole model (`weights_kind: sam-mask-decoder`).
- **Prompts from the masks.** Each object is prompted with its own box:
  - jittered by up to 10 % during training;
  - exact at evaluation;
  - at most 16 objects per picture per step.
- **Loss** as SAM's training: focal + dice (20:1), plus the IoU head regressed onto the
  IoU the mask achieved.
- **Geometry** is the processor's: pictures stretched to 1024 px, boxes scaled per axis,
  masks predicted at 256 px.
- **Score:** mIoU over held-out objects, at the picture's own size.

## Using the result

A fine-tuned SAM cannot segment on its own; it needs prompts. So it is listed in
`GET /foundation` as **"Grounded SAM · <name>"**:
- Grounding DINO tiny finds the objects;
- the fine-tuned decoder outlines them (`FoundationSpec.segmenter_id`);
- `load_segmenter(<instance id>)` loads the base checkpoint and the saved decoder over it,
  cached under its own id so the base model stays the base model.

It therefore appears wherever Grounded SAM does: the Studio, the Generator and the
Inference Viewer.

## Found live: fine-tuning can make it worse, and the runner saved it anyway

**Synthetic outlines** (70 pictures, 221 masks, stars and rings on textured ground;
split 49/14/7), 5 epochs, 141 s:

| | test mIoU |
|---|---|
| base SAM 2.1 small | **0.957** |
| "fine-tuned" (best of 5 epochs on validation) | 0.936 |

- **Why it got worse:** SAM already outlines these shapes almost perfectly, and training
  moved it away from that.
- **What the runner did:** it saved the worse model as the fine-tune.
- **Fix (doc 93's runner):** the base model now competes as **epoch 0** on validation. If
  no epoch beats it, nothing is saved and the job says so with both numbers. A test pins
  the case.

## Where fine-tuning pays: the user's own convention

**The case:** the same kind of synthetic pictures, but the user's convention outlines a
ring **including its hole** (the "whole object"), which SAM cannot guess from a box (70
pictures, 200 masks; split 49/13/8), 6 epochs, 130 s:

| | test mIoU |
|---|---|
| base SAM 2.1 small | 0.804 |
| fine-tuned (best epoch 5) | **0.957** |

**Seen on a test picture:** loaded through the app's own `load_segmenter`, base SAM
outlines the ring (IoU 0.66 and 0.67 against the convention). The fine-tuned decoder fills
the disc (0.985 and 0.975).

That is the use to recommend: teaching SAM **your** outlines and conventions, not
improving what it already does well.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

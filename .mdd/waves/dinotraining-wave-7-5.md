---
id: dinotraining-wave-7-5
title: "Wave 7.5: General Object Detection"
initiative: dinotraining
initiative_version: 8
status: in_progress
depends_on: dinotraining-wave-7
demo_state: "The user downloads RF-DETR and gets useful boxes on any image with no training at all — in the Inference Viewer, the Annotation Studio and the Dataset Generator — then fine-tunes it on their own dataset and saves it as a named model beside their trained heads."
created: 2026-08-20
hash: 28810a6e
---

# Wave 7.5: General Object Detection

## Demo-State

The user downloads **RF-DETR** from the admin panel and immediately gets useful boxes on any
image — in the Inference Viewer, and as *proposals* in the Annotation Studio and the Dataset
Generator — **with no training at all**. They then fine-tune it on their own dataset and it
is saved as a named model, listed and provenance-tracked beside their trained heads.
*(Not complete until this can be manually demonstrated.)*

## Why this wave exists, and why it is 7.5

There is no general object detector in the app. DINOv2 publishes no pretrained detection
head, so the only way to get boxes today is to train one — which Wave 4 had to do before its
own demo-state could be shown, using an imported HuggingFace dataset (doc 31). A first-time
user therefore cannot get a box out of this app without first labelling data, which is
backwards for a tool whose selling point is *starting* from proposals.

Inserted after Wave 7 rather than renumbering 8 and 9: renumbering would invalidate
cross-references in forty feature docs and in source comments, and the initiative already
paid that cost once on 2026-08-19.

## What was evaluated, and why RF-DETR won

Jan proposed four sources. All were checked on 2026-08-20 and three were rejected.

| Candidate | Loads how | Licence | General pretrained detector? |
|---|---|---|---|
| `dgcnz/dinov2_vitdet_DINO_12ep` | **detectron2**; ships only `model_final.pth` | MIT | yes, but see below |
| `itsprakhar/Yolo-DinoV2` | Ultralytics fork | **AGPL-3.0** | **no weights at all** |
| `Sompote/DINOV3-YOLOV12` | Ultralytics + transformers | **AGPL-3.0** | only a Construction-PPE model |
| **RF-DETR** | **`transformers`, already installed** | **Apache-2.0** | **yes — COCO, 91 classes** |

- **The ViTDet checkpoint is the hardest of the four, not the easiest.** A single
  `model_final.pth` is a detectron2 pickle with no `config.json`; this project refuses
  pickles by rule (doc 15) and Wave 4 deleted 920 MB of them. detectron2 also builds from
  source against pinned torch. More machinery than Depth Anything 3, which was declined.
- **`Yolo-DinoV2` cannot provide a default head** — its README states pretrained weights are
  not available. It is training code.
- **Both YOLO routes are AGPL-3.0**, inherited from Ultralytics (confirmed on PyPI). This is
  billed as a sharable, installable desktop app and **Wave 8 is packaging**; distributing
  AGPL-linked code obliges releasing the whole app under AGPL. Parked for Wave 8 to decide
  deliberately — see `.mdd/BACKLOG.md`.

**RF-DETR is a DINOv2 backbone + a C2f projector + a shallow 2-layer deformable DETR
decoder**, 300 queries, `d_model` 256, ungated, safetensors only, 116 MB for nano. Verified
present in the *installed* transformers 5.15 as `RfDetrForObjectDetection` with `rf_detr` in
the AutoConfig mapping. Its backbone being a DINOv2 is the point: "freeze the backbone,
train what sits on top" applies to it unchanged.

## Why not Faster R-CNN

Jan asked. The measured numbers answer it — the three detectors trained in doc 31:

| dataset | mAP@50 | mAP@75 | gap |
|---|---|---|---|
| thermal | 0.590 | 0.203 | −0.39 |
| blood | 0.610 | 0.154 | −0.46 |
| chess | 0.748 | **0.065** | **−0.68** |

The head **finds** objects and **localises them badly**. That is not a capacity problem
that a second stage fixes; it is resolution. `dense-detector` regresses from a single 37×37
patch grid — at 644 px input each cell is ~14 px, predicting chess pieces of ~50×88 px.

Faster R-CNN would also add an RPN, anchors, ROI-align and proposal sampling: **more
parameters to fit on 200 images**, converging slower, against a head chosen precisely
because it "converges far faster than a DETR-style head on the small datasets the Annotation
Studio produces". The same objection retires the DINO decoder from the dgcnz article.

**A ViTDet-style simple feature pyramid** is the answer instead: build four scales from the
single-scale patch grid with strided and transposed convs, feed the existing anchor-free
head. That is what ViTDet exists for — detection on a *plain, non-hierarchical* ViT, which
is exactly what a frozen DINOv2 is — and it is the same adapter the dgcnz article chose,
without detectron2 or a pickle.

## Features

| # | Doc | Feature | Depends on |
|---|---|---|---|
| 1 | 41 | rf-detr-detector | — |
| 2 | 42 | foundation-boxes-everywhere | 41 |
| 3 | 43 | multi-scale-detector | — |
| 4 | 44 | finetune-rf-detr | 41 |
| 5 | 45 | general-detection-head | 43 |

- **rf-detr-detector** — RF-DETR as a catalogue entry and a `FoundationModel` (doc 36's
  contract), rendering through the existing `boxes` render hint.
- **foundation-boxes-everywhere** — the Studio and the Generator currently offer only head
  instances whose `render_hint` is `boxes`. This is where the wave's value is: boxes from a
  foundation detector, as proposals, before anything has been trained.
- **multi-scale-detector** — the ViTDet pyramid above. Retrained on doc 31's three datasets
  so the mAP@75 change is **measured against the table above**, not asserted.
- **finetune-rf-detr** — freeze the DINOv2 backbone, train the projector and decoder, save
  as a named model with provenance. Not a `HeadInstance`: that type assumes
  `backbone_id` + head weights composed through `run_heads`' shared pass, and RF-DETR's
  decoder needs the projector's multi-scale features. It is a *trainable foundation model*.
- **general-detection-head** — train `dense-detector` on COCO val2017 (5k images, ~780 MB,
  natively in doc 31's importable format) so a general OD **head** exists.
  **Expectations are set honestly in the doc: this will be modest** — 80 classes on 5k
  images over a frozen backbone lands far below COCO state of the art. Its value is that it
  exists, proves the training path on general data, and gives the tabs a default. Anyone
  wanting a *good* general detector uses RF-DETR from feature 1.

## Open questions

- **Where a fine-tuned RF-DETR is listed.** Beside head instances is what the user asked
  for, but it is not a head. Either the head list grows a notion of "trained thing that is
  not a head", or foundation models get their own instance registry mirroring doc 12.
- **Whether fine-tuning belongs in the Head Trainer tab** or somewhere else. It is minutes
  rather than seconds, which the Trainer's live-metrics UX was not built around.

## Explicitly not in scope

- **Ultralytics-derived detectors** (YOLOv11/v12, DINOv3-YOLOv12). AGPL-3.0; parked for
  Wave 8 to decide. Recorded in the backlog with evidence.
- **detectron2**, and with it the `dinov2_vitdet_DINO` checkpoint.
- **RT-DETRv2** — Apache-2.0 and also already in transformers, so it is a cheap second
  detector *if* one is wanted. Deliberately not taken: one good general detector closes the
  gap, and a second one is breadth rather than capability.

---
id: dinotraining-wave-2
title: "Wave 2: Head Trainer"
initiative: dinotraining
initiative_version: 4
status: in_progress
depends_on: dinotraining-wave-1
demo_state: "User selects datasets, a head type (classification / detection / segmentation, plus any compatible community head they imported) and a training config with good defaults, starts training on the local device against a frozen backbone, watches live loss/metrics, and gets a saved best checkpoint that records what task and datasets it was trained on."
created: 2026-08-14
hash: 387dd20e
---

# Wave 2: Head Trainer

## Demo-State

In the **Head Trainer** tab the user selects one or more datasets built in Wave 1, chooses
a head type — **classification, object detection or segmentation** built in, plus any
**community head** they imported that is compatible with their backbone — and a training
setup with sensible defaults (save-best-only, train/val/test split, epochs, batch size, lr,
early stopping). Preprocessing is chosen internally from the backbone + head. The backbone
stays frozen; only the head trains. Training runs on the local device via a pluggable job
runner, streaming live loss/metric charts, and produces a saved best checkpoint registered
with full provenance — task, backbone version, datasets, classes and metrics — so Waves 3
and 4 can present it by what it does rather than by filename.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | backbone-feature-extractor | — | planned | — |
| 2 | head-registry | — | planned | backbone-feature-extractor |
| 3 | head-implementations | — | planned | head-registry |
| 4 | preprocessing-pipeline | — | planned | head-registry |
| 5 | training-job-runner | — | planned | head-implementations, preprocessing-pipeline |
| 6 | checkpoint-registry | — | planned | training-job-runner, head-registry |
| 7 | training-metrics-stream | — | planned | training-job-runner |
| 8 | trainer-config-ui | — | planned | head-registry, training-job-runner |
| 9 | community-head-import | — | planned | head-registry, checkpoint-registry |

### Feature notes

- **Frozen DINOv2/v3 backbone** as a feature extractor; only heads are trained. The
  extractor publishes a *backbone capability descriptor* (model version, patch size, embed
  dim, output stride, available layers) — this is what head compatibility is checked against.
- **head-registry is the central abstraction of this wave.** A head type is a registry entry,
  never an enum branch in the trainer. Each entry declares:
  - `task` (classification / detection / segmentation / depth / …)
  - output tensor schema and the target format it trains against
  - loss function and metric set
  - preprocessing requirements (resize/crop/normalisation, target resampling)
  - backbone compatibility constraints (which versions, patch sizes, embed dims)
  - a render hint so Wave 3/4 know how to draw its output
  Everything downstream — trainer, metrics stream, checkpoint format, inference viewer,
  generator — dispatches off this contract. Adding a head type must never require touching
  the training loop.
- **Built-in head types this wave: classification, object detection, segmentation.**
  Detection uses an **anchor-free dense head** (FCOS/CenterNet-style, per-patch classification
  + box regression on the ViT patch grid, NMS at inference). Segmentation is included
  deliberately as the first *dense per-pixel* task, to prove the registry contract against a
  genuinely different output shape rather than two near-identical box/label tasks.
  **Depth is deferred** — it needs a data path the Annotation Studio does not produce and its
  own eval story; it lands later as an additional registry entry, additively.
- **community-head-import:** users can add third-party heads that fit their backbone.
  **Safetensors only, from a HuggingFace repo id — `.pt`/`.pth` pickle checkpoints are
  refused outright**, since `torch.load` on a pickle is arbitrary code execution and this app
  is installed by strangers. Each community head requires a manifest declaring backbone
  version, patch size, embed dim and task; the import validates it against the backbone
  capability descriptor and explains *why* a head is incompatible rather than just greying it
  out. Guide the user: show which of their downloaded backbones a head would work with.
- Training config with good defaults: split method, save-best-only, epochs, lr, batch,
  early stopping, augmentation on/off.
- Job runner interface (local now) designed so a remote/hyperscaler runner drops in later
  (Wave 6).
- Live metrics streamed to the UI (WebSocket/SSE) with loss + the metric set the head's
  registry entry declares (acc / mAP / mIoU / …) — the stream must not hardcode metric names.
- **Checkpoint provenance is a hard requirement, not a nice-to-have.** Every registered
  checkpoint records: head type, backbone version it was trained against, the datasets and
  class list used, the training config, and its best metrics. Waves 3 and 4 present heads to
  the user by *what they do and what they were trained on* — never by filename. This
  descriptor is the cross-tab contract for the whole rest of the initiative.

## Open Research

- ~~Detection-head design on a frozen backbone~~ → **resolved 2026-08-17: anchor-free dense
  head** (FCOS/CenterNet-style, per-patch classification + box regression on the ViT patch
  grid, NMS at inference). DETR-style set prediction was rejected for slow convergence on
  the small datasets Wave 1 produces.
- Metric set + charts per head type; best-model selection criterion (declared by the head's
  registry entry, not hardcoded in the trainer or the chart component).
- Reproducibility: seeds, config snapshot saved alongside each checkpoint.
- Segmentation targets from Wave 1 data: the Annotation Studio produces boxes, not masks —
  decide whether segmentation trains on box-derived weak masks, or requires a mask-capable
  dataset the user brings. Resolve before feature 3 (head-implementations).
- Which community heads actually exist as safetensors for DINOv2/v3 today — needed to make
  the import guidance concrete rather than theoretical.

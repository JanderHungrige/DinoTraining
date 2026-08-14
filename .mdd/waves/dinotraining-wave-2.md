---
id: dinotraining-wave-2
title: "Wave 2: Head Trainer"
initiative: dinotraining
initiative_version: 1
status: planned
depends_on: dinotraining-wave-1
demo_state: "User selects datasets + head type + training config (good defaults), starts training on the local device, watches live loss/metrics, and gets a saved best checkpoint."
created: 2026-08-14
hash: c2d3fb8a
---

# Wave 2: Head Trainer

## Demo-State

In the **Head Trainer** tab the user selects one or more datasets built in Wave 1, chooses
a head type (classification, object detection, …), and a training setup with sensible
defaults (save-best-only, train/val/test split, epochs, batch size, lr, early stopping).
Preprocessing is chosen internally from the backbone + head. Training runs on the local
device via a pluggable job runner, streaming live loss/metric charts, and produces a saved
best checkpoint registered for use in Wave 3.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | backbone-feature-extractor | — | planned | — |
| 2 | head-architectures | — | planned | backbone-feature-extractor |
| 3 | preprocessing-pipeline | — | planned | — |
| 4 | training-job-runner | — | planned | — |
| 5 | trainer-config-ui | — | planned | — |
| 6 | training-metrics-stream | — | planned | training-job-runner |
| 7 | checkpoint-registry | — | planned | training-job-runner |

### Feature notes

- Frozen DINOv2/v3 backbone as a feature extractor; heads trained on top.
- Head types start with **classification** and **object detection**; extensible registry.
- Training config with good defaults: split method, save-best-only, epochs, lr, batch,
  early stopping, augmentation on/off.
- Job runner interface (local now) designed so a remote/hyperscaler runner drops in later
  (Wave 6).
- Live metrics streamed to the UI (WebSocket/SSE) with loss + task metrics (acc / mAP).
- Checkpoints registered so Inference (Wave 3) and the Generator (Wave 4) can select them.

## Open Research

- Detection-head design on a frozen backbone (linear + anchors vs. lightweight DETR head).
- Metric set + charts per head type; best-model selection criterion.
- Reproducibility: seeds, config snapshot saved alongside each checkpoint.

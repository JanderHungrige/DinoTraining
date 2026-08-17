---
id: dinotraining
title: DinoTraining
status: active
version: 4
hash: 18a1938e
created: 2026-08-14
---

# DinoTraining

## Overview

DinoTraining is a sharable, installable desktop application that turns the loop of
**annotate → train → infer → generate more data** into a single tool built around
self-supervised vision backbones (DINOv2 / DINOv3) and open-vocabulary detection
(Grounding DINO).

The user works across tabs:

1. **Annotation Studio** — pick a local (later: online) image dataset, type a text
   prompt, and Grounding DINO proposes bounding boxes. The user marks each box
   **positive / negative / unclear**, can draw boxes by hand and label them, and the
   images + labels are stored in a format ready to train a DINOv2/v3 head. A counter
   tracks images processed and label counts.
2. **Head Trainer** — choose one or more datasets, a head type, and classic training
   options (save-best-only, train/val/test split, epochs, lr, …) with good defaults. The
   DINO backbone stays **frozen**; only the head is trained. Head types are entries in a
   **head registry** — each declares its task, output schema, loss, metrics, preprocessing
   needs and backbone compatibility — so new head types are added without touching the
   training loop. Built in: classification, object detection, segmentation (depth and others
   follow additively). Users can also **import community heads** that fit their backbone
   version. Image preprocessing is chosen internally from the selected backbone + head. Live
   progress and metrics are shown. Training runs on a pluggable job runner (local device now;
   hyperscaler GPUs later). Every saved checkpoint records **what task and which datasets it
   was trained on**, so it can be presented meaningfully everywhere else in the app.
3. **Inference Viewer** — run a DINO backbone + one or more trained heads on an image or
   video stream; show original vs. results side-by-side (labels, boxes, masks, or whatever
   the head produces — driven by the head's render hint). Heads are listed by task, training
   datasets and metrics, never by bare filename.
4. **Dataset Generator** — use the backbone + trained expert head(s) as an auto-annotator
   over new data (same review/mark UX as tab 1), saving results in the training format so
   the next head can be trained. Closes the data flywheel.
5. **Admin / Models** — manage model downloads (kept out of the installer to keep it
   small): download/remove DINOv2, DINOv3 (gated — needs a HuggingFace token), and
   Grounding DINO; import community heads (safetensors only) with a compatibility check
   against the installed backbones; manage the cache dir; show device/compute status.

**Architecture:** Tauri (Rust shell) + React/TypeScript UI + a FastAPI + PyTorch sidecar
for all ML. The web core (React + FastAPI) is deliberately reusable for the future website.

**Compute:** Local device now (CUDA / Apple MPS / CPU fallback), with the trainer written
as a swappable job runner so hyperscaler GPUs can be added later.

**Later:** a website version where compute and object storage from the main hyperscalers
(AWS / GCP / Azure) can be connected.

## Open Product Questions

- [x] App architecture & packaging → Tauri + React + FastAPI/PyTorch sidecar
- [x] Compute target → local now, cloud-ready job runner for later
- [x] Repo → public `JanderHungrige/DinoTraining`, `main` + `dev`
- [x] Model set → DINOv2 + DINOv3 (gated) + Grounding DINO from the start
- [x] Dataset on-disk format → COCO JSON export + native `dataset.json` sidecar. COCO
      cannot express `unclear`, box provenance, or the prompt, so the native side is the
      source of truth and COCO is a generated export of positives only. (Wave 1)
- [x] DINOv3 gated access → offered but marked unavailable without a token, with a
      per-model licence link; DINOv2 stays fully usable tokenless. (Wave 1)
- [x] Detection head approach on a frozen DINO backbone → **anchor-free dense head**
      (FCOS/CenterNet-style: per-patch classification + box regression over the ViT patch
      grid, NMS at inference). Chosen over a DETR-style decoder because set-prediction
      heads converge too slowly for the few-hundred-image datasets Wave 1 produces, and
      the backbone is frozen so the head must learn fast on its own. (Wave 2)
- [x] Head types & extensibility → heads are **registry entries**, not enum branches. Each
      declares task, output schema, loss, metrics, preprocessing needs, backbone
      compatibility and a render hint; trainer, metrics stream, checkpoints, viewer and
      generator all dispatch off that contract. Built in for Wave 2: classification,
      detection, segmentation. Depth is deferred as a later additive entry — it needs a data
      path the Annotation Studio does not produce. (Wave 2)
- [x] Community heads → users may import third-party heads matching their backbone version.
      **Safetensors from a HuggingFace repo id only; `.pt`/`.pth` pickles are refused**,
      because `torch.load` on a pickle is arbitrary code execution in an app installed by
      strangers. A manifest (backbone version, patch size, embed dim, task) is required and
      validated against the backbone capability descriptor, with an explanation when
      incompatible. (Wave 2)
- [x] Trained-head provenance → every checkpoint records head type, backbone version,
      datasets, class list, config and best metrics. Waves 3 and 4 present heads by what they
      do and what they were trained on. This descriptor is the cross-tab contract. (Wave 2)
- [ ] Code-signing / notarization for macOS + Windows installers (Wave 5).
- [ ] Which hyperscaler(s) to support first for the website (Wave 6).

## Waves

| Wave | File | Demo-state | Status |
|------|------|------------|--------|
| Wave 1 | waves/dinotraining-wave-1.md | User picks a local image folder, types a prompt, sees Grounding DINO boxes, marks/draws boxes as pos/neg/unclear, and the app saves a structured dataset with a live counter — after downloading models from the admin tab. | complete |
| Wave 2 | waves/dinotraining-wave-2.md | User selects datasets, a head type (classification / detection / segmentation, plus any compatible community head they imported) and a training config with good defaults, starts training on the local device against a frozen backbone, watches live loss/metrics, and gets a saved best checkpoint that records what task and datasets it was trained on. | in_progress |
| Wave 3 | waves/dinotraining-wave-3.md | User loads an image or webcam/video, selects a backbone + trained head(s), and sees original vs. annotated results side-by-side in real time. | planned |
| Wave 4 | waves/dinotraining-wave-4.md | User runs trained expert head(s) over new images, reviews/marks predictions, and saves a new dataset ready to train another head. | planned |
| Wave 5 | waves/dinotraining-wave-5.md | A new user installs a signed macOS/Windows/Linux installer; on first run it downloads required weights via the admin tab and the full annotate→train→infer loop works. | planned |
| Wave 6 | waves/dinotraining-wave-6.md | The app runs as a website; a user connects a cloud GPU for training and cloud object storage for datasets/models. | planned |

---
id: dinotraining
title: DinoTraining
status: active
version: 2
hash: 76c5a76d
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
2. **Head Trainer** — choose one or more datasets, a head type (classification,
   object detection, …), and classic training options (save-best-only, train/val/test
   split, epochs, lr, …) with good defaults. Image preprocessing is chosen internally
   from the selected backbone + head. Live progress and metrics are shown. Training runs
   on a pluggable job runner (local device now; hyperscaler GPUs later).
3. **Inference Viewer** — run a DINO backbone + one or more trained heads on an image or
   video stream; show original vs. results side-by-side (labels, boxes, or whatever the
   head produces).
4. **Dataset Generator** — use the backbone + trained expert head(s) as an auto-annotator
   over new data (same review/mark UX as tab 1), saving results in the training format so
   the next head can be trained. Closes the data flywheel.
5. **Admin / Models** — manage model downloads (kept out of the installer to keep it
   small): download/remove DINOv2, DINOv3 (gated — needs a HuggingFace token), and
   Grounding DINO; manage the cache dir; show device/compute status.

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
- [ ] Detection head approach on a frozen DINO backbone (e.g. simple DETR-style / linear +
      anchor head) — pick in Wave 2 research.
- [ ] Code-signing / notarization for macOS + Windows installers (Wave 5).
- [ ] Which hyperscaler(s) to support first for the website (Wave 6).

## Waves

| Wave | File | Demo-state | Status |
|------|------|------------|--------|
| Wave 1 | waves/dinotraining-wave-1.md | User picks a local image folder, types a prompt, sees Grounding DINO boxes, marks/draws boxes as pos/neg/unclear, and the app saves a structured dataset with a live counter — after downloading models from the admin tab. | complete |
| Wave 2 | waves/dinotraining-wave-2.md | User selects datasets + head type + training config (good defaults), starts training on the local device, watches live loss/metrics, and gets a saved best checkpoint. | planned |
| Wave 3 | waves/dinotraining-wave-3.md | User loads an image or webcam/video, selects a backbone + trained head(s), and sees original vs. annotated results side-by-side in real time. | planned |
| Wave 4 | waves/dinotraining-wave-4.md | User runs trained expert head(s) over new images, reviews/marks predictions, and saves a new dataset ready to train another head. | planned |
| Wave 5 | waves/dinotraining-wave-5.md | A new user installs a signed macOS/Windows/Linux installer; on first run it downloads required weights via the admin tab and the full annotate→train→infer loop works. | planned |
| Wave 6 | waves/dinotraining-wave-6.md | The app runs as a website; a user connects a cloud GPU for training and cloud object storage for datasets/models. | planned |

---
id: dinotraining-wave-1
title: "Wave 1: App Shell, Annotation Studio & Model Admin"
initiative: dinotraining
initiative_version: 1
status: in_progress
depends_on: none
demo_state: "User picks a local image folder, types a prompt, sees Grounding DINO boxes, marks/draws boxes as pos/neg/unclear, and the app saves a structured dataset with a live counter — after downloading models from the admin tab."
created: 2026-08-14
hash: f44a6e72
---

# Wave 1: App Shell, Annotation Studio & Model Admin

## Demo-State

User launches the desktop app, opens the **Admin/Models** tab and downloads
Grounding DINO + a DINO backbone, then opens **Annotation Studio**, points it at a local
image folder, types a text prompt, and sees Grounding DINO bounding boxes overlaid on each
image. They mark each box **positive / negative / unclear**, can draw new boxes by hand and
label them the same way, and the images + labels are saved to a structured on-disk dataset.
A counter shows images processed and per-label counts.
*(This wave is not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | app-shell | .mdd/docs/01-app-shell.md | complete | — |
| 2 | model-manager | .mdd/docs/02-model-manager.md | complete | app-shell |
| 3 | dataset-store | — | planned | app-shell |
| 4 | grounding-dino-annotator | — | planned | model-manager, dataset-store |
| 5 | annotation-canvas | — | planned | app-shell |
| 6 | annotation-workflow | — | planned | annotation-canvas, grounding-dino-annotator, dataset-store |

### Feature notes

- **app-shell** — Tauri (Rust) window hosting a React/TS tabbed UI (Studio / Trainer /
  Inference / Generator / Admin). Spawns the FastAPI+PyTorch sidecar as a Tauri sidecar
  binary, health-checks it, and proxies `/api/v1/*`. Establishes the frontend↔backend
  contract and dev workflow (`tauri dev`).
- **model-manager** — Admin tab + backend model registry & download manager. Lists
  available models (Grounding DINO `IDEA-Research/grounding-dino-tiny|base`, DINOv2
  `facebook/dinov2-*`, DINOv3 `facebook/dinov3-*` — gated), downloads via `huggingface_hub`
  with progress, stores an HF token (from `.env` / admin UI) for gated DINOv3, shows the
  detected compute device (CUDA/MPS/CPU) and cache location, allows removal. Weights live
  outside the installer.
- **dataset-store** — On-disk dataset format + a small SQLite metadata index. Stores images
  (by reference or copy), boxes with `label ∈ {positive, negative, unclear}`, provenance
  (grounding-dino vs hand-drawn), and the prompt. Exposes a counter service (images
  processed, per-label counts). Decide COCO-compatible export vs native format here.
- **grounding-dino-annotator** — Backend `/api/v1/annotate` endpoint: given an image (or a
  folder batch) + text prompt + thresholds, run Grounding DINO
  (`AutoModelForZeroShotObjectDetection`) and return proposed boxes + scores.
- **annotation-canvas** — React canvas component: render an image with overlaid boxes,
  click a box to cycle/set pos/neg/unclear, draw a new box by dragging and label it,
  keyboard shortcuts. Pure UI, backend-agnostic.
- **annotation-workflow** — Ties it together: folder picker, image navigation, run prompt,
  review boxes on the canvas, persist labels to dataset-store, live counter UI, next/prev.

## Open Research

- Grounding DINO batching + threshold defaults (box/text thresholds) for good recall on
  arbitrary prompts.
- Dataset format decision: COCO JSON export + native sidecar vs. YOLO — must be trivially
  consumable by the Wave 2 trainer.
- Tauri sidecar packaging of a Python/PyTorch environment (PyInstaller/embedded venv) —
  spike early since it affects Wave 5.

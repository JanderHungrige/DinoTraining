# DinoTraining — Architecture

> Living document. Started at project kickoff (2026-08-14). Full build plan in `.mdd/`.

## Goals

1. One desktop app for the CV data loop: **annotate → train → infer → generate more data**.
2. Sharable & installable, small installer (weights download on demand).
3. Local compute now (CUDA / Apple MPS / CPU), hyperscaler GPUs later.
4. A web-reusable core so a future website (Wave 6) shares most code.

## High-level shape

```
Tauri shell (Rust)  ──spawns──▶  FastAPI + PyTorch sidecar (Python)
     │                                  ▲
     │ hosts webview                     │ HTTP  /api/v1/*
     ▼                                  │
React + TypeScript UI  ────────────────┘
```

- **Why Tauri + web UI + Python sidecar:** the ML stack (Grounding DINO, DINOv2/v3, training)
  is Python-only, so ML lives in a FastAPI sidecar. The UI is web tech so the *same* React +
  FastAPI code can later be deployed as a website. Tauri keeps the shell small vs. Electron.

## Components

### Frontend — `apps/frontend/` (React + TS, Vite)
- Tabs: Annotation Studio · Head Trainer · Inference Viewer · Dataset Generator · Admin.
- One typed API client for `/api/v1`. Shared components: annotation canvas, side-by-side
  viewer, overlay renderer, counter.

### Desktop shell — `apps/desktop/` (Tauri, Rust)
- Owns the window + webview, spawns/monitors the Python sidecar (Tauri sidecar binary),
  native file/folder pickers, webcam permission. Proxies to the sidecar.

### Backend — `backend/` (FastAPI + PyTorch)
- `app/api/`      — `/api/v1` routers: `annotate`, `train`, `infer`, `generate`, `models`, `admin`.
- `app/ml/`       — Grounding DINO annotator, DINOv2/v3 backbones, head registry, preprocessing.
- `app/training/` — trainer + **pluggable job runner** (local now; remote GPU later).
- `app/datasets/` — on-disk dataset store + SQLite metadata index + counter service.
- `app/core/`     — settings (pydantic-settings), device detection, model download manager.

## Key decisions (locked)

| Decision | Choice |
|----------|--------|
| Packaging | Tauri + React + FastAPI/PyTorch sidecar |
| Compute | Local (CUDA/MPS/CPU) now; pluggable runner for hyperscaler later |
| Models | DINOv2 + DINOv3 (gated) + Grounding DINO |
| Repo | Public `JanderHungrige/DinoTraining`, `main` + `dev` |
| Metadata DB | SQLite via a single shared connection module |

## Open questions (see initiative doc)

- Dataset on-disk format: COCO-compatible export + native sidecar vs. YOLO.
- DINOv3 gated-access UX + graceful DINOv2 fallback.
- Detection-head design on a frozen backbone.
- Installer signing/notarization (Wave 5).
- First hyperscaler target (Wave 6).

## Models & access

| Model | HF id (example) | Access |
|-------|------------------|--------|
| Grounding DINO | `IDEA-Research/grounding-dino-tiny` / `-base` | Open |
| DINOv2 | `facebook/dinov2-base` | Open |
| DINOv3 | `facebook/dinov3-vitb16-pretrain-lvd1689m` | **Gated** (accept license + `HF_TOKEN`) |

Weights cache in `DINO_MODEL_CACHE_DIR`, never bundled, never committed.

## Torch install note

`torch`/`torchvision` must be installed per-platform (CUDA build on Linux/Windows w/ NVIDIA,
default build for Apple MPS/CPU). The `pyproject.toml` pins minimums; the actual index/variant
is chosen by the install script (`scripts/`) or the packaged sidecar per target.

## Data flywheel

Wave 1 produces datasets → Wave 2 trains heads → Wave 3 runs them → Wave 4 uses trained heads
to auto-annotate new data back into Wave 1's dataset store → retrain. Each generated dataset
records provenance (which head/version produced it).

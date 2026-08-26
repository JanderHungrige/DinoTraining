# DinoTraining

A sharable, installable desktop app for the full computer-vision data loop:
**annotate → train → infer → generate more data**, built around DINOv2 / DINOv3
backbones and Grounding DINO open-vocabulary detection.

> Status: 🏗️ **Wave 1 in progress** — the app shell runs: a Tauri window hosting the
> React tabbed UI, with the FastAPI sidecar spawned and health-checked at startup.
> The Studio and Admin tabs are still stubs. See [`.mdd/`](.mdd/) for the wave plan.

## What it does

| Tab | Purpose |
|-----|---------|
| **Annotation Studio** | Point at a local image folder, type a prompt → Grounding DINO proposes boxes. Mark each **positive / negative / unclear**, draw boxes by hand, save to a training-ready dataset with a live counter. |
| **Head Trainer** | Pick datasets + head type (classification, detection, …) + training config (good defaults). Live progress/metrics. Preprocessing chosen internally per backbone+head. Pluggable job runner (local now, cloud later). |
| **Inference Viewer** | Run a backbone + trained head(s) on an image or webcam/video; original vs. results side-by-side. |
| **Dataset Generator** | Use trained expert head(s) to auto-annotate new data, review/mark, save as a new training set — closing the data flywheel. |
| **Admin / Models** | Download/remove models (kept out of the installer to stay small), manage the HF token for gated DINOv3, cache dir, and compute device. |

## Architecture

```
┌────────────────────────── Tauri desktop shell (Rust) ──────────────────────────┐
│  React + TypeScript UI  ── HTTP /api/v1 ──▶  FastAPI + PyTorch sidecar (Python)  │
│  (apps/frontend)                             (backend/)                          │
│                                              • Grounding DINO (annotate)         │
│                                              • DINOv2 / DINOv3 backbones         │
│                                              • head training (pluggable runner)  │
│                                              • inference / dataset generation    │
└──────────────────────────────────────────────────────────────────────────────┘
```

- **UI:** React + TypeScript (`apps/frontend`)
- **Desktop shell:** Tauri (`apps/desktop`)
- **ML backend:** FastAPI + PyTorch sidecar (`backend/`)
- **Compute:** local CUDA / Apple MPS / CPU now; hyperscaler GPU job runner later
- **The React + FastAPI core is intentionally reusable for the future website (Wave 6).**

## Models

| Model | Use | Access |
|-------|-----|--------|
| Grounding DINO (`IDEA-Research/grounding-dino-tiny` / `-base`) | Open-vocab box proposals | Open |
| DINOv2 (`facebook/dinov2-*`) | Backbone / features | Open |
| DINOv3 (`facebook/dinov3-*`) | Backbone / features | **Gated** — accept the license on HF and set `HF_TOKEN` |

Weights are **not** bundled; they download on first run / via the Admin tab.

## Repo layout

```
apps/frontend/     React + TypeScript UI (Vite)
apps/desktop/      Tauri (Rust) shell
backend/           FastAPI + PyTorch ML service
  app/api/         /api/v1 routers
  app/ml/          grounding dino, dino backbones, heads, preprocessing
  app/training/    trainer + pluggable job runner
  app/datasets/    dataset store + counter
  app/core/        config, model download manager
project-docs/      architecture & design notes
scripts/           dev / build / release scripts
.mdd/              Manual-Driven Development plan (initiative + waves)
```

## Getting started

Prerequisites: **Python 3.11+** (3.12 recommended), **Node 22 LTS or 24+**, **Rust 1.85+**.

```bash
git clone https://github.com/JanderHungrige/DinoTraining
cd DinoTraining
cp .env.example .env            # add HF_TOKEN only if you need gated DINOv3

# Backend
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -e "backend[dev]"

# Frontend  (--legacy-peer-deps works around an npm 10.9 resolver bug)
npm install --prefix apps/frontend --legacy-peer-deps

# Desktop shell — only if you want the Tauri window. `web` and `backend` do not need it.
npm install --prefix apps/desktop
```

**`rustc -vV` must print a `host:` line.** Check it before the first desktop run:

```bash
command -v rustc && rustc -vV
```

Without that line Tauri cannot work out what it is building for and aborts on an unwrap
inside its own CLI, naming a line number in a Rust file you do not have.
`./scripts/dev.sh` checks for it and prints what rustc actually said. Two ways to get
there, and they need opposite fixes:

- **`Symbol not found` / dyld abort** — a Rust install linked against a library that has
  since moved, typically Homebrew rust after an `llvm` upgrade. `brew reinstall rust`.
- **`no default toolchain`** — rustup has none selected. `rustup default stable`.

Installing Rust *both* ways is the usual road into this, because the two `rustc` binaries
compete on `PATH` and `rustup default` does not affect the Homebrew one. Keep one.

Then run whichever loop you need:

```bash
./scripts/dev.sh            # full desktop app — Tauri window + Vite + backend
./scripts/dev.sh web        # browser-only at localhost:1420 (no Rust build — fastest loop)
./scripts/dev.sh backend    # backend alone on 127.0.0.1:8756
```

Quality gates, all of which must be clean before a feature is done:

```bash
(cd backend && pytest && ruff check . && mypy app tests)
npm run test --prefix apps/frontend && npm run typecheck --prefix apps/frontend
(cd apps/desktop/src-tauri && cargo clippy --all-targets)
```

## Development plan

This project is built wave-by-wave with [MDD](.mdd/):

1. **Wave 1** — App shell + Annotation Studio + Model Admin
2. **Wave 2** — Head Trainer
3. **Wave 3** — Inference Viewer
4. **Wave 4** — Dataset Generator
5. **Wave 5** — Packaging & Distribution (installers)
6. **Wave 6** — Website + hyperscaler compute/storage

See [`.mdd/initiatives/dinotraining.md`](.mdd/initiatives/dinotraining.md).

## Branches

- `main` — stable
- `dev` — active development (default working branch)

## License

See [LICENSE](LICENSE). Note: model weights are governed by their own licenses
(DINOv3 is gated/commercial-licensed by Meta; DINOv2 and Grounding DINO by their respective terms).

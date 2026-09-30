# DinoTraining

**Teach a computer to find things in your pictures, without being a data scientist.**

DinoTraining is a desktop app for the whole loop of a computer-vision project:
1. label pictures, with a model proposing the labels;
2. prepare the data so that training can work;
3. train a model;
4. look at what it learned;
5. use it to label the next batch faster.

It is built on Meta's DINOv2 / DINOv3, SAM 2 / SAM 3 and Grounding DINO, and on RF-DETR.
Everything runs on your own machine, and your pictures are never uploaded.

---

## Contents

- [What it does, in one minute](#what-it-does-in-one-minute)
- [Install and start](#install-and-start)
  - [Option A: installer](#option-a-installer)
  - [Option B: from source](#option-b-from-source)
  - [First steps after starting](#first-steps-after-starting)
- [Features](#features)
  - [Start here](#start-here)
  - [Annotation Studio](#annotation-studio)
  - [Prepare data](#prepare-data)
  - [Training](#training)
  - [Inference Viewer](#inference-viewer)
  - [Dataset Generator](#dataset-generator)
  - [Inspect datasets](#inspect-datasets)
  - [Library](#library)
  - [Admin / Models](#admin--models)
  - [Connection (AI assistants and API)](#connection-ai-assistants-and-api)
- [A typical project, end to end](#a-typical-project-end-to-end)
- [Models](#models)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Development](#development)
- [License](#license)

---

## What it does, in one minute

- **Label pictures fast.** Type what you are looking for ("a signal", "a bolt"), and a
  model proposes boxes or outlines. You accept, reject or correct them.
- **Get the data right before training.** The app checks your dataset and explains, in
  plain words, what would make training fail: pictures that are copies of each other,
  classes with too few examples, objects too small for the model to see. It then splits
  the data so the test score cannot be fooled by near-identical pictures.
- **Train.** Either train a small "head" on a frozen DINO backbone (seconds to minutes),
  or fine-tune a whole model (RF-DETR, SAM 2, SAM 3, DINO backbones) to your data.
- **See the result.** Run models side by side on pictures or videos.
- **Close the loop.** Let a trained model annotate new pictures, review them, and train
  again.
- **Drive it from an AI assistant.** Claude or another MCP client can run the same steps
  and get the same explanations.

---

## Install and start

### Option A: installer

Installers for macOS (`.dmg`), Windows (`.exe`, NSIS) and Linux (`.deb`) are built from
version tags and published as **draft releases** on GitHub.

> ⚠️ **The installers are not code-signed yet.**
> - **macOS** blocks the first launch (Gatekeeper). Right-click the app → *Open* →
>   *Open*.
> - **Windows** shows a SmartScreen warning. *More info* → *Run anyway*.
> - **Linux** is `.deb` only.

Model weights are **not** in the installer; you download them in the app (see below).
The installer is CPU/Apple-GPU only; NVIDIA GPU support is a separate download offered in
the app.

### Option B: from source

**Prerequisites:**
- Python **3.11+** (3.12 recommended);
- Node **22 LTS or 24+**;
- Rust **1.85+**, only for the desktop window.

```bash
git clone https://github.com/JanderHungrige/DinoTraining
cd DinoTraining
cp .env.example .env            # add HF_TOKEN only if you need the gated models

# Backend
python3.12 -m venv backend/.venv
source backend/.venv/bin/activate
pip install -e "backend[dev]"

# Frontend  (--legacy-peer-deps works around an npm 10.9 resolver bug)
npm install --prefix apps/frontend --legacy-peer-deps

# Desktop shell (only for the desktop window; the browser mode does not need it)
npm install --prefix apps/desktop
```

**Start**, in one of three ways:

```bash
./scripts/dev.sh            # desktop app: Tauri window + UI + backend
./scripts/dev.sh web        # in the browser at http://localhost:1420 (no Rust needed)
./scripts/dev.sh backend    # backend only, on http://127.0.0.1:8756
```

<details>
<summary>Troubleshooting the desktop build (Rust)</summary>

`rustc -vV` must print a `host:` line; `./scripts/dev.sh` checks this. Without it Tauri
aborts inside its own CLI. The two usual causes need opposite fixes:

- **`Symbol not found` / dyld abort**: Homebrew's rust was linked against a library that
  has since moved (often after an `llvm` upgrade). Fix: `brew reinstall rust`.
- **`no default toolchain`**: rustup has none selected. Fix: `rustup default stable`.

Having Rust installed both ways is the usual cause: the two `rustc` binaries compete on
`PATH`. Keep one.
</details>

### First steps after starting

1. **Admin / Models → download the starter set.** Five models, about 1.1 GB, enough to
   label, train and run. Anything else downloads on demand.
2. **Start here** explains the app in five minutes.
3. **Annotation Studio**: point it at a folder of pictures and describe what to find.

---

## Features

The app is organised as tabs, in the order a project runs through them.

### Start here

A plain-language introduction:
- what a backbone, a head and fine-tuning are;
- which model is good for what, with numbers measured in this app;
- what the app cannot do yet.

### Annotation Studio

Label a folder of pictures.

- **Proposals:** from a text prompt (Grounding DINO, or Grounded SAM / SAM 3 for
  outlines), from a general detector, or from a head you trained yourself.
- **Review:** mark each proposal *positive*, *negative* or *unclear*. Unclear regions are
  ignored by training rather than taught wrongly.
- **Edit:** draw, move and resize boxes by hand, and pick or rename classes.
- **Masks and boxes:** show masks, boxes or both. A segmented object is saved as an outline
  with its box derived from it.
- **Datasets:** saved with a live counter of what you have; exportable as standard COCO.

### Prepare data

A guided path from a dataset to a **recipe** that training follows. It is written for
people who have never trained a model: every step recommends a setting and says why, and
experts can jump straight to any step.

1. **Check the data (audit).** Reads every picture and annotation and reports, in plain
   words, what would make training go wrong, judged for the model you chose:
   - too few pictures, or classes with too few examples;
   - very unequal classes;
   - objects too small for the model's input;
   - unreadable files and copies of the same picture;
   - class names spelled two ways.

   Each finding shows the pictures to look at.
2. **Fix what is safe.** Leave out copies or unreadable files, and merge, rename or leave
   out classes. Nothing is ever deleted, and every fix can be undone.
3. **Split.** Training, validation and test sides that cannot leak: frames of one video
   and photos of one scene stay on one side. Random splits of video can make a score look
   42 % better than the model is.
4. **What the model sees.** Your own pictures exactly as the model receives them, at its
   resolution, with objects that are too small marked red. If the objects are too small,
   the app plans training on **tiles**.
5. **Unequal classes.** Choose between counting rare classes more and showing them more
   often. A recommendation comes from your numbers, with the reason.
6. **Changed copies (augmentation).** Presets for everyday photos, outdoor / road / rail,
   indoor, microscopy and documents, previewed on your own pictures. Boxes always move
   with the picture, and nothing is mirrored where a mirror changes the meaning (signs,
   text, left/right).
7. **Save the recipe.** A versioned record of all the above. If the data changes later,
   the recipe says so, and training refuses to use an out-of-date one.

**Importing a published dataset** (COCO / Roboflow) is checked first: how its boxes are
written, whether every image exists, and class names that look like duplicates.

### Training

Two kinds of training, side by side.

**A DINO head** (fast). A small head (classification, detection or segmentation) is
trained on a frozen DINOv2 / DINOv3 backbone, in seconds to minutes. You can see live loss
and metrics.
- **With a recipe:** the stored split, tiles and class handling are used, and the finished
  run reports a **test score**, measured on pictures that played no part in training or in
  choosing the best round.
- **Without a recipe:** the run still works, and says that its data was not prepared.

**Fine-tune a model** (stronger, slower). A whole foundation model adapts to your data:

| Model | Learns from | Typical use |
|---|---|---|
| RF-DETR | boxes | detection where the numbers matter |
| SAM 2.1 | one outline per object | outlines in your own style or convention |
| SAM 3 | outlines named by a phrase | "find every *X*", with your notion of *X* |
| DINOv2 / DINOv3 backbone | one class per picture, or outlines | a backbone adapted to your domain, with its head |

For each model the app shows **what your training data must look like** and checks your
dataset against it before you can start, naming anything missing and how to fix it. Every
run then compares the **original model** with the **fine-tuned one** on the same held-out
pictures. If fine-tuning did not help, nothing is saved.

Measured in this app, on data with a leak-free split:
- RF-DETR reached 0.62 test mAP on blood cells, against 0.41 for a DINO head.
- SAM 2 went from 0.80 to 0.96 mIoU on an outline convention it could not know.

**Settings, explained.** Every setting a model's training honours is shown as
"Plain name (technical term)", e.g. *Rounds (epochs)* or *Box looseness (box jitter)*, with
a **?** that explains it and gives the default and why. Basic settings come first; the rest
sit under *Advanced settings*. Changed values are marked and can be reset.

**No recipe yet?** Where a recipe can be chosen and none is, a card explains what a recipe
is and offers **Create the default recipe**: Prepare data's steps with every recommendation
taken, in one click. **Open Prepare data** goes there at this dataset and model instead.

### Inference Viewer

Run trained heads and foundation models on one picture, side by side with the original.
- **Video:** play back a folder or a video file with every frame's result.
- **Tiles:** a head trained on tiles is run on tiles automatically, so small objects in
  large pictures are found as they were in training.

### Dataset Generator

Let a trained model (or a prompt) annotate new pictures or a video, and review what it
proposes.
- **Speed:** auto-propose and auto-save beside Previous/Next.
- **Autoplay:** propose → a short pause to look → save → next, stoppable at any moment.
- **Hidden mode:** runs without drawing, showing only progress.
- **Ask when unclear:** stops on predictions whose score is in a band you set.

### Inspect datasets

Play back a dataset (its videos, folders and loose pictures) with all stored annotations
drawn on. Coloured bars under the player show where each class appears; click one and
jump to its first, previous or next occurrence.

### Library

Everything you have made in one place: datasets, trained heads and fine-tuned models,
with what they were trained on and how well they scored. Rename, delete, or open a
dataset's folder.

### Admin / Models

- **Models:** download and remove models. The starter set is one click. Gated models
  (DINOv3, SAM 3) need a HuggingFace token and the licence accepted on HuggingFace.
- **Settings:** the model cache folder and the compute device (CPU / Apple GPU / NVIDIA).
- **GPU support:** an NVIDIA GPU download, and a check that your GPU is actually used.

### Connection (AI assistants and API)

- **MCP:** the app runs an MCP server on its own backend, so an AI assistant can drive it.
  Task-shaped tools include import, prepare, train, fine-tune, annotate, run and export,
  and their descriptions carry the same explanations the UI shows. For Claude Code:

  ```bash
  claude mcp add --transport http dinotraining http://127.0.0.1:8756/mcp
  ```

- **API guide:** a guide written for an AI assistant (the order of calls, and the traps),
  plus the full REST API under `http://127.0.0.1:8756/api/v1`, reachable from a "Copy for
  your AI" button.
- **Local only:** everything is bound to this machine, without authentication.

---

## A typical project, end to end

1. **Annotation Studio:** label 100–300 pictures from a text prompt; accept, reject and
   correct.
2. **Prepare data:** audit, fix, split, check "what the model sees", save a recipe.
3. **Training:** train a DINO head with the recipe, or fine-tune RF-DETR / SAM for the
   stronger result. Read the test score.
4. **Inference Viewer:** look at the results on new pictures or a video.
5. **Dataset Generator:** let the trained model annotate the next folder; review and
   save.
6. **Inspect datasets:** play it back, then prepare and train again.

---

## Models

Weights are **not** bundled. They download on demand in *Admin / Models* and are cached
locally.

| Model | Used for | Access |
|---|---|---|
| Grounding DINO (tiny, base) | boxes from a text prompt | open |
| SAM 2.1 (small, base-plus, large) | outlines from boxes; with Grounding DINO: Grounded SAM | open |
| SAM 3 | outlines from a phrase, in one model | **gated** (Meta approves access) |
| DINOv2 (small, base, large) | backbone for heads | open |
| DINOv3 (ViT-B/16, ViT-L/16) | backbone for heads | **gated** (accept the licence, set `HF_TOKEN`) |
| RF-DETR (nano, small, base) | general detector; fine-tunable | open |
| Depth Anything V2 (small, base, large) | depth maps | open |

Each model's licence applies to its weights and to anything fine-tuned from them. The
app shows the licence next to every model.

---

## Configuration

Settings live in `.env` (copy `.env.example`); all are optional.

| Variable | Meaning |
|---|---|
| `HF_TOKEN` | HuggingFace token, for the gated models. Never commit it. |
| `DINO_MODEL_CACHE_DIR` | where model weights are stored |
| `DINO_DATA_DIR` | where datasets, recipes and trained models are stored |
| `DINO_DEVICE` | `auto`, `cpu`, `mps` or `cuda` |
| `DINO_API_HOST` / `DINO_API_PORT` | backend address (default `127.0.0.1:8756`) |

**Default data folder:**
- macOS: `~/Library/Application Support/DinoTraining`;
- Windows: `%LOCALAPPDATA%\DinoTraining`;
- Linux: `~/.local/share/DinoTraining`.

---

## Architecture

```
┌──────────────────────── Tauri desktop shell (Rust) ────────────────────────┐
│  React + TypeScript UI  ── HTTP /api/v1 ──▶  FastAPI + PyTorch sidecar      │
│  (apps/frontend)                             (backend/)                     │
│                                              • annotation (Grounding DINO,  │
│                                                SAM 2/3, trained heads)      │
│                                              • data preparation             │
│                                              • head training, fine-tuning   │
│                                              • inference, dataset generation│
│                                              • MCP server at /mcp           │
└─────────────────────────────────────────────────────────────────────────────┘
```

- **Compute:** CPU, Apple GPU (MPS) or NVIDIA CUDA, all local.
- **Metadata:** SQLite, through one shared connection module.
- **Datasets and weights:** on disk, never in the repository.

```
apps/frontend/     React + TypeScript UI (Vite)
apps/desktop/      Tauri (Rust) shell and installers
backend/app/
  api/v1/          REST routes
  datasets/        dataset store, import/export, tiling
  prep/            data preparation: audit, fixes, split, input plan, recipes
  ml/              backbones, heads, training, inference, foundation models
  finetune/        fine-tuning: requirements, runner, per-model adapters
  mcp/             MCP server and tools
  docs/            the agent guide
backend/tests/     pytest suite
scripts/dev.sh     development launcher
.mdd/              design docs, waves and the handoff (start with .mdd/HANDOFF.md)
```

---

## Development

**Quality gates.** Everything must be clean before a feature is done:

```bash
(cd backend && pytest && ruff check . && mypy app tests)
npm run test --prefix apps/frontend && npm run typecheck --prefix apps/frontend
(cd apps/desktop/src-tauri && cargo clippy --all-targets)
```

**How the project is built.** Wave by wave, with Manual-Driven Development: every feature
has a design doc in [`.mdd/docs/`](.mdd/docs/) written before the code, and every wave is
verified in the running app. [`.mdd/HANDOFF.md`](.mdd/HANDOFF.md) is always the current
state.

| Wave | Content |
|---|---|
| 1–4 | App shell, Annotation Studio, model admin, head training, Inference Viewer, Dataset Generator |
| 5–8 | Foundation models, fine-tuning RF-DETR, packaging and installers |
| 9 | Generator autopilot, Inspect datasets |
| 10 | Look and feel |
| 11 | Guided data preparation |
| 12 | Fine-tuning SAM 2, SAM 3 and DINO backbones |
| 13 | Every training setting explained, default recipes |
| 14 | Annotating for the model: phrases, hard negatives, mask editing (planned) |
| 15 | English and German (planned) |
| 16 | Website and cloud compute (planned) |

**Branches:**
- `main` is stable;
- `dev` is where development happens;
- each wave is built on its own `feat/…` branch.

---

## License

[MIT](LICENSE) for the code. Model weights are governed by their own licences: DINOv3
and SAM 3 are gated by Meta under custom terms, and the other models are under their
respective licences, shown in the app.

# DinoTraining backend

FastAPI + PyTorch ML sidecar for the annotate → train → infer → generate loop.
Spawned and health-checked by the Tauri shell (`apps/desktop`); see the root
[README](../README.md) for the whole picture.

## Setup

Python 3.11+ (3.12 recommended — the dev venv and `mypy` target it):

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Torch installs a platform-appropriate wheel automatically (CUDA on Linux/Windows,
MPS on Apple silicon). To force a specific build, install torch first from the
[PyTorch index](https://pytorch.org/get-started/locally/), then run the command above.

## Run

```bash
python -m app                       # reads .env from the repo root
uvicorn app.main:app --reload       # or, with autoreload for development
```

Binds `127.0.0.1:8756` by default — loopback only, never expose it off-machine.
Readiness probe: `GET /api/v1/health`. Interactive docs: `/docs`.

## Quality gates

```bash
pytest          # all tests must pass
ruff check .    # no warnings
mypy app tests  # strict, clean
```

## Layout

```
app/api/v1/     versioned routers — every route registers in router.py
app/core/       config, logging, error shaping
app/ml/         Grounding DINO, DINO backbones, heads, preprocessing
app/training/   trainer + pluggable job runner
app/datasets/   dataset store + counter
```

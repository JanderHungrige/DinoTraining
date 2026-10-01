---
id: 125-dependency-lock
title: Dependency Lock — One Hashed Lock File, PyTorch Variants cpu / cu126 / cu130 from pytorch.org
edition: DinoTraining
depends_on: [56-sidecar-bundling]
relates: [126-bundled-python, 127-first-run-setup, 128-accelerator-switch, 129-update-sync]
source_files:
  - backend/pyproject.toml
  - backend/uv.lock
  - scripts/dev.sh
  - README.md
  - .github/workflows/lock-check.yml
routes: []
models: []
test_files:
  - backend/tests/test_dependency_lock.py
data_flow: greenfield
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [installer, uv, lockfile, pytorch, cuda, mps, packaging]
path: Installer/Lock
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "pytorch.org publishes no sha256 for two files: torchvision 0.28.0+cu126 and +cu130 for Windows (win_amd64). uv installs them unverified; every other file in the lock is hashed. Recheck on the next PyTorch bump."
  - "The lock pins Python 3.12 (requires-python >=3.12,<3.13): onnxruntime has no macOS arm64 wheels for every Python the old >=3.11 allowed. The bundled Python (doc 126) is 3.12."
security_read_sites: []
sister_projects: []
---

# 125 — Dependency Lock

## Purpose

- **What changes:** users install the backend's packages on their own machine (doc 126).
  Every machine must get **exactly the versions the tests ran with**, from the official
  sources, verified by hash.
- **Why it matters:** an unpinned `torch>=2.2` on a user's machine next year is a different
  program.

## The variants

PyTorch 2.13 is published for `cpu`, `cu126` and `cu130`; `cu128` and `cu129` do not exist
for it (checked on download.pytorch.org, 2026-09-30).

| Extra | torch / torchvision from | For |
|---|---|---|
| `cpu` | Mac: PyPI (its wheels carry MPS); Windows/Linux: `download.pytorch.org/whl/cpu` | Apple Silicon, and PCs without a usable NVIDIA card |
| `cu126` | `download.pytorch.org/whl/cu126` | NVIDIA with a driver ≥ 560 |
| `cu130` | `download.pytorch.org/whl/cu130` | NVIDIA with a driver ≥ 580 (includes RTX 50xx) |

- The extras **conflict**: exactly one is installed (`[tool.uv] conflicts`).
- The PyTorch indexes are `explicit`, so nothing else is ever taken from them.
- **The lock covers three platforms only** (`[tool.uv] environments`): macOS arm64,
  Windows x86_64, Linux x86_64. PyTorch has no Intel-Mac wheels since 2.3, so an Intel Mac
  cannot resolve; doc 127 refuses it before anything is downloaded.
- **The backend is not installed as a package** (`package = false`). It runs from its
  source with `python -m app`, as in development today.
- **Runtime dependencies used by the app are declared, not inherited:** `httpx` (doc 123's
  MLflow client) came in only through `mcp`.

## Developers

- `uv sync --extra cpu --extra dev --extra export` gives the same environment as a user.
- `pip install -e ".[cpu,dev,export]"` still works; pip ignores the uv sources, which is
  right on a Mac.
- `dev.sh` and the README say so.

## Checked

- **`test_dependency_lock.py`:**
  - the lock exists and is current with `pyproject.toml` (`uv lock --check`);
  - it holds a torch for each variant and platform, with hashes;
  - `torch` is never an unconditional dependency.
- **A CI job** (`lock-check.yml`) runs `uv lock --check`, and `uv sync --frozen --extra cpu`
  plus the backend test suite on the three platforms. The versions users get are the
  versions tested.

## Verified (2026-09-30)

- **The lock:** `uv lock` resolved 128 packages. `uv.lock` holds `torch 2.13.0` from PyPI
  for the Mac, and `+cpu`, `+cu126`, `+cu130` from download.pytorch.org for Windows and
  Linux, all hashed; torchvision the same, with the two exceptions above.
- **A fresh environment from the lock** (`uv sync --frozen --extra cpu --extra dev --extra
  export`):
  - installed in 32 s on the M1;
  - torch 2.13.0 with MPS available, 1.0 GB on disk;
  - the whole backend suite in that environment: 1893 passed, 1 skipped (the lock check,
    no uv inside).
- **`test_dependency_lock.py` (7):**
  - the lock is current;
  - every machine has its torch, with hashes;
  - torch is never an unconditional dependency;
  - httpx is declared.
- **CI:** `lock-check.yml` runs the lock check, a CPU install and the backend tests on
  macOS, Windows and Linux runners.
- **The README and `dev.sh`** now install from the lock (`uv sync`), or with pip and the
  `cpu` extra.

## Bugs

(none yet)

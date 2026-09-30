---
id: 127-first-run-setup
title: First-Run Setup — Hardware Detection, Variant Choice, uv Progress and a Dino Run While It Installs
edition: DinoTraining
depends_on: [126-bundled-python, 125-dependency-lock]
relates: [128-accelerator-switch, 129-update-sync, 131-installer-smoke-ci]
source_files:
  - apps/desktop/src-tauri/src/setup.rs
  - apps/desktop/src-tauri/src/progress.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/Cargo.toml
  - apps/frontend/src/App.tsx
  - apps/frontend/src/setup/SetupGate.tsx
  - apps/frontend/src/setup/SetupScreen.tsx
  - apps/frontend/src/setup/DinoRun.tsx
  - apps/frontend/src/setup/runRules.ts
  - apps/frontend/src/setup/shell.ts
  - apps/frontend/src/setup/MachineSummary.tsx
  - apps/frontend/src/setup/SetupFailureNotice.tsx
  - apps/frontend/src/setup/SetupTips.tsx
  - apps/desktop/src-tauri/src/setup_flow.rs
  - apps/desktop/src-tauri/src/runtime.rs
  - apps/frontend/src/setup/setup.css
  - apps/frontend/src/i18n/en/setup.ts
  - apps/frontend/src/i18n/de/setup.ts
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/setup.rs (unit tests)
  - apps/desktop/src-tauri/src/progress.rs (unit tests)
  - apps/frontend/src/setup/SetupGate.test.tsx
  - apps/frontend/src/setup/SetupScreen.test.tsx
  - apps/frontend/src/setup/runRules.test.ts
  - apps/frontend/src/components/MlflowBackfill.test.tsx (flaky wait fixed on the way)
  - apps/frontend/src/components/finetune/FoundationFinetunePanel.test.tsx (flaky wait fixed on the way)
data_flow: greenfield
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [installer, setup, uv, cuda, nvidia, mps, progress, animation, tauri]
path: Installer/Setup
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The last step (ready, then the app) was verified by unit tests and in the browser with a simulated shell, not in the real window: this session had no screen-recording or accessibility permission, and the screen was locked. The shell side was verified live up to 'Setup finished'."
  - "Dino Run was seen in Chromium (browser pane), not yet in the macOS WebKit window; roundRect has a fallback for older WebKitGTK."
  - "WebKit pauses the scripts of a hidden window. The screen no longer polls, but its progress and the switch to the app catch up only when the window is visible again."
security_read_sites: []
sister_projects: []
---

# 127 — First-Run Setup

## Purpose

- **Where doc 126 left it:** the first start installs the `cpu` variant without asking,
  and the window says "Starting" for about a minute.
- **What this adds:**
  - a setup screen in the app window, before the backend exists;
  - the machine detected, and the right PyTorch variant chosen for it;
  - progress a person can follow, and failures in plain words with a way on;
  - something to do while it downloads (Jan: "die Wartezeit kurzweiliger gestalten").

## The flow

1. **The shell decides whether setup is needed** (Rust, `setup_status` command): a
   packaged app whose runtime is not ready (doc 126). A checkout never needs it, and a
   browser (web dev mode) has no shell and skips it.
2. **The setup screen shows:**
   - what was found ("Apple M1, GPU through MPS" / "NVIDIA RTX 4070, driver 581.15" / "no
     NVIDIA card");
   - what will be installed and roughly how big: "PyTorch for the CPU, about 1 GB" or
     "PyTorch with CUDA 13.0, about 5 GB";
   - one button, **Install**. With an NVIDIA card, a second choice: **CPU only (smaller)**.
3. **Installing** (`setup_install(variant)` command):
   - checks first: free disk space, then whether the package servers answer;
   - runs `uv sync` (doc 126), streaming progress events;
   - starts the backend and **returns only when it answers `/health`**. The shell waits,
     not the screen: WebKit pauses the timers of a hidden window, and a screen polling
     `/health` stayed on "starting" while the backend was long up (found live).
4. **When the backend answers**, the screen offers **Open DinoTraining**. Nobody played
   the game? Then it opens straight away.
5. **Unattended:** `DINO_SETUP_AUTO=<variant>` makes the screen install that variant
   without a click (a variant the machine cannot take is ignored). For admins and doc
   131's smoke test.
6. **The screen's steps go to the app log** (`setup_report`: shown, installing,
   starting, ready, opened, failed), next to uv's output: what a user sends when the
   first start fails, and what the smoke test reads.

## The variant (Rust, pure function, unit-tested)

| Machine | Variant | Why |
|---|---|---|
| macOS, Apple Silicon | `cpu` | PyPI's Mac wheels carry MPS: the GPU is included |
| macOS, Intel | refused | PyTorch has no Intel-Mac wheels since 2.3 (doc 125) |
| Windows/Linux x86_64, NVIDIA driver ≥ 580 | `cu130` | CUDA 13.0, includes RTX 50xx |
| Windows/Linux x86_64, NVIDIA driver ≥ 560 | `cu126` | CUDA 12.6 |
| Windows/Linux x86_64, older NVIDIA driver | `cpu` | "Your NVIDIA driver (535) is too old for CUDA 12.6; update it to use the GPU" |
| Windows/Linux x86_64, no NVIDIA | `cpu` | |
| anything else (Linux arm64, Windows arm64) | refused | the lock covers three platforms (doc 125) |

- **The NVIDIA card is found with `nvidia-smi`**
  (`--query-gpu=name,driver_version --format=csv,noheader`). It ships with every NVIDIA
  driver; without it there is no usable card. The first GPU decides.
- **A refused machine** sees why, and no Install button. Nothing is downloaded.

## Checks before the download

- **Disk space** (`fs4::available_space` on the runtime folder):
  - `cpu` needs 3 GB (measured: Python 73 MB, environment 869 MB, cache 821 MB);
  - CUDA needs 10 GB.
  - Too little: "Needs about 3 GB free on <disk>; 1.2 GB are free."
- **Online:** one request to `https://pypi.org/simple/` with a 10 s timeout. Failing:
  "No internet connection. The first start downloads Python and PyTorch once; after that
  DinoTraining works offline."
- **A failed `uv sync`** reports uv's last line. Output that names a connection or DNS
  failure is reported as offline instead.
- **Try again** repeats the install. uv's cache keeps what was already downloaded, so a
  retry continues rather than starting over.

## Progress (Rust, `progress.rs`, pure and unit-tested)

uv's output, measured in doc 126's run:

```
Downloading cpython-3.12.14-macos-aarch64-none (download) (23.9MiB)
 Downloaded cpython-3.12.14-macos-aarch64-none (download)
Downloading torch (106.1MiB)
 Downloaded torch
Prepared 68 packages in 25.64s
Installed 68 packages in 417ms
```

- **Weighted by megabytes:** each `Downloading X (size)` adds to the total, and each
  `Downloaded X` adds its size to what is done. uv starts all its downloads at once, so
  the total is known early.
- **Phases:** `python` → `packages` → `installing` (after `Prepared`) → `done` (after
  `Installed`).
- **The event** (`setup-progress`): `{phase, done_mb, total_mb, current}`, where `current`
  is the last package finished. Throttled by the parser: only lines that change something
  emit.

## The wait: Dino Run

- **A small running game** in the setup screen, on a canvas: the dino runs, rocks and
  ferns come towards it, **Space, ↑ or a click** jumps. A hit ends the round and shows the
  score and the best score this session; a jump starts the next.
- **Nobody has to play.** Without input the dino runs on its own and jumps by itself, so
  the screen is a calm animation.
- **The progress bar is the ground:** its filled part grows under the dino, with the
  percentage and megabytes next to it, in words for screen readers too.
- **Tips while waiting:** one sentence at a time about what the app does (backbone, head,
  phrases, the Generator), changing every 9 seconds.
- **The game's rules are a pure module** (`runRules.ts`: step, jump, collision, spawning
  from a seeded random source), tested without a canvas. The component only draws.
- **`prefers-reduced-motion`:** no game and no running animation; the progress bar and
  the tips stay.

## Windows

- `uv`, `nvidia-smi` and the environment's `python.exe` are console programs. Each is
  started with `CREATE_NO_WINDOW`, or a GUI app would flash (or, for the backend, keep
  open) a black console window.

## Language

- English and German (`setup` namespace, doc 111); technical terms stay English
  (MPS, CUDA, driver, PyTorch).

## Verified (2026-09-30)

- **Rust (15 unit tests):** every row of the variant table (Apple Silicon, Intel Mac
  refused, driver 581 → cu130, 565 → cu126, 535 → CPU with the reason, Linux arm64
  refused); `nvidia-smi` output parsed; a disk check that names needed and free space;
  the progress parser on doc 126's real uv output (megabyte weighting, GiB/KiB,
  phases, lines that change nothing emit nothing); offline recognised from uv's words.
- **Frontend (21 tests):**
  - the rules of Dino Run: jump, landing, no double jump, collisions, restart keeping
    the best score, no teleport after a pause, a seeded course; **the autopilot runs ten
    minutes on five seeds without a crash**;
  - the screen: a Mac gets one button with MPS named, an NVIDIA PC gets GPU first and
    CPU second, an Intel Mac gets the reason and no button; progress, the current
    package and the tips; the app opens by itself when nobody played and waits for the
    click when someone did; offline and disk failures with the numbers, and Try again
    installs the same variant; an unattended install starts without a click; German,
    with "3,5 GB";
  - the gate: outside the shell the app renders at once, with its environment it shows
    the app, without it the setup, and an older shell that cannot answer still shows the
    app.
- **In the browser with a simulated shell** (narrow pane): the screen, the choice
  buttons, the bar at 31 % with "61 von 190 MB" and "scipy geladen", Dino Run running,
  the tips. Found and fixed: `.setup` already belonged to the Studio's session form and
  gave the screen its layout (renamed `.firstrun`); the percentage wrapped.
- **The real app, unattended, into an empty runtime folder** (`DINO_SETUP_AUTO=cpu`):
  shown → installing → uv installed 68 packages → starting → backend healthy → "Setup
  finished" in **52 s**; Python 72 MB, environment 868 MB, cache 818 MB. A second start
  into the same folder skipped the setup and was healthy in 3 s.
- **Found on the way:** the MLflow backfill test waited exactly as long as the
  component's first poll (1 s) and failed one run in three; it now waits 3 s.
- Found on the way: FoundationFinetunePanel's start-button wait (1 s) failed under the full suite's load; it now waits 3 s.

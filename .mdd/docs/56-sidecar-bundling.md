---
id: 56-sidecar-bundling
title: Freezing the Sidecar — the Spike That Constrains Wave 8
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-8
wave_status: in_progress
depends_on: []
relates: [54-distribution-licensing, 01-app-shell]
source_files:
  - backend/packaging/entry.py
  - backend/packaging/build_sidecar.py
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/tauri.conf.json
  - apps/desktop/src-tauri/binaries/README.md
  - .gitignore
routes: []
models: []
test_files: []
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [packaging, pyinstaller, tauri, sidecar, torch, installer-size, spike]
path: Packaging/Sidecar
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**Verified on macOS/arm64 only.** PyInstaller does not cross-compile, so Windows and Linux are unproven — and Windows is where the size problem is worst. The hidden-import list is the one that worked here; another platform may need more."
  - "**The `.dmg` is 292 MB, not 636.** This doc first reasoned the installer size from the sidecar size and was wrong by a factor of two — compression matters more than expected. Corrected in the body; the Windows and Linux equivalents are still unmeasured."
  - "**No automated test.** Freezing takes ~2.5 minutes and produces 636 MB; nothing in `pytest` can assert against it. The spike was run by hand and the numbers below are from that run."
  - "`--collect-all transformers` is heavy-handed. It is also the only thing that works: transformers resolves model classes through a lazy registry keyed by config strings, so no import statement mentions `RfDetrForObjectDetection`. A curated list would break silently whenever a new model id was added to the catalogue."
  - "The frozen build reads `DINO_DATA_DIR` and `DINO_MODEL_CACHE_DIR` exactly as the dev one does, so a packaged app shares a developer's store on the same machine. Correct for now; worth revisiting when there is a real installer."
  - "Nothing yet checks that the release build does not carry a restricted model (doc 54). The sidecar excludes weights entirely, so this is about the *cache*, not the binary — but CI still needs the guard."
sister_projects: []
---

# 56 — Freezing the Sidecar

## Purpose

Wave 8's own plan says to spike this first because it constrains everything. It does, and
not in the way the plan expected.

## It works

PyInstaller freezes the FastAPI + PyTorch + transformers sidecar and the result **runs**:

```
health      {"status":"ok","version":"0.0.1","device":"mps"}   <- torch found the GPU
models      15 catalogued, 6 installed
RF-DETR     25 boxes on a real photo — person x20, tie x4, cell phone x1, 195 ms
```

That last line is the one that matters. transformers resolves model classes through a lazy
registry keyed by config strings, so nothing statically references
`RfDetrForObjectDetection`; a frozen build that starts cleanly can still fail the moment a
model is loaded. This one loads real weights from the cache and predicts.

Two things had to be right, and both fail *late* rather than at build time:

1. **uvicorn's runtime string lookups.** It selects its loop, protocol and lifespan
   implementations by name, so PyInstaller's analysis sees no reference. The build
   succeeds, the server starts, and the first request fails on an import.
2. **`multiprocessing.freeze_support()`.** Without it a frozen binary re-executes *itself*
   for every spawned worker on macOS and Windows — the process forks until something gives
   up, and the port never binds.

## The number that changes Wave 8

| | |
|---|---|
| development venv | 1.1 GB |
| production-only venv (no mypy/ruff/pytest) | **986 MB** |
| **frozen sidecar** | **636 MB** |

Freezing *helps* — it strips 350 MB of unused code — but the floor is torch. Weights were
never the size problem this wave planned around; **the runtime is.**

**Correction, from actually building an installer (doc 58):** the `.app` is 1.0 GB and the
`.dmg` is **292 MB**. DMG compression squeezes torch's dylibs hard, so the *download* is far
smaller than the on-disk figure — a distinction this doc originally got wrong by reasoning
from the sidecar size alone.

## The decision this forces, and it is Jan's

The torch wheel is not one thing. Measured against the official index, cp312:

| variant | Windows | Linux |
|---|---|---|
| CPU-only | **111 MB** | ~200 MB |
| CUDA 12.4 | **2532 MB** | 768 MB |

`resolve_device` picks CUDA → MPS → CPU, so this app *supports* NVIDIA GPUs today. On
Windows, shipping that support costs **2.5 GB of wheel** before anything else is added.

Three ways out, and they are product choices rather than build details:

1. **CPU-only wheels everywhere.** Installers around 350–650 MB. macOS keeps MPS (it is in
   the default wheel); Windows and Linux lose NVIDIA acceleration entirely — on a *training*
   app, for the users most likely to have a GPU.
2. **CUDA wheels on Windows and Linux.** A 2.5 GB Windows installer. Nobody downloads that
   twice.
3. **CPU by default, GPU as a download.** Matches what this app already does with weights —
   nothing heavy ships, the admin tab fetches what you need. It is the most work and the
   only option that does not force a loss.

**Recommendation: (3), with (1) as the shipping default until it exists.** Not decided here;
it needs Jan.

## What changed in the code

`sidecar.rs` predicted this in Wave 1: *"in a packaged build it becomes a bundled binary;
only `resolve_command` changes"*. That held. `SidecarConfig::resolve()` now looks for a
frozen binary beside the executable and falls back to `python -m app` from the venv.

**The frozen binary wins when it exists**, deliberately: a packaged app must never fall
through to a developer's venv that happens to be on the same machine. It would run a
different build of the backend than the one shipped and behave correctly enough that nobody
would notice until the two diverged.

One naming trap is worth stating because it is the usual first failure: the build script
names the output with the target triple, because that is what Tauri's *bundler* looks for.
The file **installed** beside the app has the triple stripped. `frozen_sidecar()` looks for
the stripped name.

## Consequences for the rest of Wave 8

- **`release-ci` is a build matrix**, not a runner. PyInstaller does not cross-compile and
  the torch wheel differs per platform.
- **`auto-update` needs thinking about.** A 640 MB app that ships a full replacement on
  every patch is a bad citizen; Tauri's updater does not diff.
- **The sidecar is built from a *production* venv**, not the dev one — otherwise mypy, ruff
  and pytest are frozen in alongside the app.

## Verified

Built and run on macOS/arm64 on 2026-08-21: 143 s to freeze, 636 MB output, server healthy
on MPS, and a real RF-DETR inference returning 25 correct boxes. `cargo check` clean on the
Rust change.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

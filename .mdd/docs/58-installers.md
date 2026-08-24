---
id: 58-installers
title: A Real Installer — Built, Launched, and Then Codified as CI
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-8
wave_status: in_progress
depends_on: [56-sidecar-bundling, 57-gpu-support-download]
relates: [54-distribution-licensing, 01-app-shell]
source_files:
  - .github/workflows/release.yml
  - apps/desktop/src-tauri/tauri.release.conf.json
  - apps/desktop/src-tauri/BUNDLING.md
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/desktop/src-tauri/src/lib.rs
  - backend/bundling/build_sidecar.py
  - backend/pyproject.toml
routes: []
models: []
test_files: []
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [packaging, installers, tauri, ci, release, macos, windows, linux]
path: Packaging/Installers
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**Windows does not build.** It fails inside the bundler with both MSI and NSIS, ~350 s into the step. The cause is unidentified because reading the job log needs admin rights on the repository. A long-paths mitigation is in the workflow and is **unverified**."
  - "**AppImage cannot package this payload.** Isolated across runs 2 and 3: `appimage,deb` fails and `deb` alone passes. Linux therefore ships a `.deb` only, which excludes users on distributions that do not take one."
  - "The `.build/Scripts` assumption for the Windows venv turned out to be correct — the sidecar built there in every run."
  - "**Nothing is signed.** An unsigned `.app` is Gatekeeper-blocked on first launch and an unsigned `.exe` gets a SmartScreen warning. The publish job therefore creates a **draft** release — a human decides when something unsigned reaches users. Signing is Wave 8 feature 4 and needs Jan's certificates, which I cannot hold."
  - "**`npm ci || npm install`** in the workflow is a hedge: this project needs `--legacy-peer-deps` and `npm ci` fails without a lockfile in sync. It should be one command once that is settled."
  - "The release job does not build the CUDA sidecar (doc 57), so the GPU download still has no artefact. It is a second matrix leg with a different `--index-url`, deliberately left until the CPU one is proven on all three platforms."
  - "No `auto-update` wiring. A 292 MB download per patch is a bad citizen and Tauri's updater does not diff — worth solving before the first update rather than after."
sister_projects: []
---

# 58 — Installers

## Purpose

Turn doc 56's spike into a real installer, then write the CI from what actually worked
rather than from what should.

## It builds, and it runs

```
Finished `release` profile [optimized] in 1m 33s
Bundling DinoTraining.app      1.0 GB
Bundling DinoTraining_0.0.1_aarch64.dmg   292 MB
```

Launched from the bundle, not from a checkout:

```
sidecar   …/DinoTraining.app/Contents/Resources/sidecar/dinotraining-sidecar
health    {"status":"ok","device":"mps"}
RF-DETR   25 boxes — person x20, tie x4, cell phone x1 — 88 ms
```

**That is Wave 8's demo-state, minus signing.** A user double-clicks, the app starts its own
backend, and the full loop is available with no Python, no venv and no checkout.

## The correction worth reading

Doc 56 reasoned the installer size from the sidecar size and got it wrong by a factor of
two. The sidecar is 636 MB and the `.app` is 1.0 GB, but the **`.dmg` is 292 MB** — DMG
compression squeezes torch's dylibs hard. The number that matters to a user is the download,
and it is far better than predicted.

## Three things only building found

**1. `externalBin` cannot take a directory.** PyInstaller's `--onedir` output is an
executable plus `_internal/`, and `externalBin` takes a single file. The `--onefile`
alternative unpacks 636 MB to a temp directory on *every launch* — seconds of churn before
the port binds, with the app looking hung throughout. The sidecar ships as a Tauri
**resource** instead, and `resource_dir` comes from Tauri's own path API rather than being
derived from `current_exe`, because the answer differs per platform.

Once that changed, **the target triple in the sidecar's name became vestigial** — it existed
only because `externalBin` requires it. The name is now fixed on every platform and the
triple is printed for the release job to label its artefact with.

**2. Adding `bundling/` broke `pip install .`** — and would have broken it for Jan too.
setuptools' flat-layout discovery finds every top-level directory and refuses when there is
more than one, so `app` plus `bundling` was an error. `[tool.setuptools.packages.find]` now
says what ships.

**3. The directory was called `packaging/` for about an hour**, which put
`backend/packaging/` on `sys.path` ahead of the **real `packaging` PyPI package** — imported
by setuptools, transformers and huggingface-hub. `pip install .` failed immediately; the
frozen build would have failed later and far more mysteriously.

## The CI, written second on purpose

`release.yml` is a **matrix, not a runner**, because PyInstaller does not cross-compile and
the torch wheel differs per platform. Two things in it are load-bearing:

**`--index-url .../whl/cpu` is not optional.** Without it, Windows and Linux pull the CUDA
build and the installer goes from ~300 MB to over 2.5 GB (doc 56). GPU support is a separate
download (doc 57), and this line is what keeps the default small.

**A guard that CI can enforce and a warning cannot.** Doc 54's Admin panel warns a *human*
about restricted models. CI does not read warnings, and a runner with a populated model
cache would happily ship someone else's weights. The job fails if any `.safetensors`,
`.bin` or `pytorch_model*` is inside the bundle. Run against the real macOS bundle: passes.

**The publish job creates a draft.** Nothing is signed yet, and an unsigned build reaching
users is Gatekeeper-blocked on macOS and SmartScreen-warned on Windows. A human decides.

## What CI actually said

Three runs against a `v0.0.1` tag on 2026-08-21. The value is in what each one ruled out.

| run | Windows | Linux | macOS |
|---|---|---|---|
| 1 | fail | fail | fail |
| 2 | fail | fail | **pass** |
| 3 | fail | **pass** (deb) | **pass** |

**Run 1 — the workflow, not the platforms.** All three built the sidecar and then failed
identically at `npm run tauri build`. `@tauri-apps/cli` is a devDependency of
`apps/desktop`, and the workflow installed only `apps/frontend`. There is no npm workspace
root, so both need installing. It worked locally because `apps/desktop/node_modules` was
already there — a difference between my machine and a clean checkout that only CI could
show.

**Run 2 — macOS green, and the failures moved into the bundler.** Windows and Linux both
spent 367 s and 230 s inside "Build the installer", which is long enough to have finished
the Rust compile. Whatever was wrong was in bundling, not in building.

**Run 3 — AppImage is the Linux problem.** Narrowing `appimage,deb` to `deb` alone made
Linux pass. That isolates it: AppImage repacks the entire tree through `linuxdeploy`, and
the tree is 636 MB of PyInstaller `_internal` with thousands of files. `deb` is a tarball
and does not care. macOS's dmg does not care either, which is why it passed from run 2.

**Windows still fails, and NSIS is not the fix.** It fails with NSIS exactly as it did with
MSI, at ~350 s — again past the compile, again in the bundler. So it is not WiX-specific.
The cause is **not yet identified**: reading the job log needs admin rights on the
repository, which this session does not have.

A long-paths step is now in the workflow as the standard mitigation — PyInstaller's
`_internal` nests deeply and the runner workspace is already `D:\a\repo\repo\`, so 260
characters is a plausible ceiling. **It is unverified.** It has not been shown to be the
fix and should not be described as one.

## Verified

Built and launched on macOS/arm64 on 2026-08-21, with the sidecar built through the
committed `bundling/build_sidecar.py` and the bundle produced by the committed release
config. The running process was confirmed to be the one inside the `.app`, not a leftover
from a checkout. `cargo check` clean; the workflow parses and its weights guard was run
against the real bundle.

**Windows and Linux are unproven.** They are the next thing to try, and the matrix exists so
that one run answers for all three.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

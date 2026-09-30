---
id: dinotraining-wave-15-7
title: "Wave 15.7: Installer — bundled Python, PyTorch from the source, GPU chosen at setup, Mac via Homebrew"
initiative: dinotraining
initiative_version: 15
status: planned
depends_on: dinotraining-wave-15-6
demo_state: "On a clean Windows PC with an NVIDIA card, a ~70 MB installer installs the app; its first start detects the GPU, downloads PyTorch with CUDA from pytorch.org with progress (resumable), and the backend reports CUDA; the same installer on a PC without NVIDIA sets up CPU, a Mac with Apple Silicon sets up MPS, an Intel Mac is told plainly it is not supported. Switching CPU ⇄ GPU later works from the GPU panel, and an app update only fetches what changed. CI installs and starts the app on all three platforms."
created: 2026-09-30
hash: 27035511
---

# Wave 15.7: Installer — bundled Python, PyTorch from the source, GPU chosen at setup

**Jan's decisions (2026-09-30):**
- Windows matters: the app must install and run there.
- **GPU support should be loaded by the installer, from the official sources.** It is not
  hosted by us: "PyTorch und CUDA können doch so gezogen werden."
- **Installer only.** The website is decided later (Wave 16 stays as it is for now).
- **No paid signing** ("I will not give Apple 100 € for an open-source project"). The Mac
  keeps its Tauri window, because the browser cannot open folders. It is installed by
  **Homebrew formula** or a **one-line script**, never by a browser download.

## Why the build changes

- **Today (Wave 8):** the backend is **frozen with PyInstaller** into one 636 MB sidecar,
  with CPU PyTorch inside. A frozen binary cannot swap its PyTorch. So GPU support meant
  building and hosting a second ~2.4 GB sidecar (doc 57, never built), which is over
  GitHub's 2 GB file limit and redistributes NVIDIA's libraries.
- **Instead,** as ComfyUI Desktop and InvokeAI do: ship a **standalone Python**
  (`python-build-standalone`), our code and **`uv`**. The packages are installed on the
  user's machine from **pytorch.org and PyPI**, pinned with hashes in a lock file.
- **What that gives:**
  - an installer of ~50–80 MB instead of 292 MB;
  - the GPU chosen at setup, with no hosting by us;
  - NVIDIA's libraries come from the source, not from us;
  - no PyInstaller freezing, which Windows virus scanners often flag;
  - updates that fetch only what changed;
  - an AppImage for Linux that becomes possible again (it failed on size in Wave 8).
- **What stays:** the Tauri shell, the release pipeline, the NSIS / dmg / deb installers,
  and the GPU detection and panel of doc 57. Tauri already has a "Python module" launch
  mode (`Launch::Module`, today dev-only).

## Platforms

| Machine | PyTorch | Accelerator |
|---|---|---|
| Mac, Apple Silicon (M1–M4) | standard wheel from PyPI (~70 MB) | MPS (Metal), with `PYTORCH_ENABLE_MPS_FALLBACK=1` |
| Mac, Intel | — | **not supported** (PyTorch has had no Intel-Mac builds since 2.3): a clear message, no half-install |
| Windows / Linux, NVIDIA with a new enough driver | CUDA wheel from `download.pytorch.org/whl/cu12x` + NVIDIA libraries from PyPI (~2.5 GB) | CUDA |
| Windows / Linux, no NVIDIA or an old driver | CPU wheel from `download.pytorch.org/whl/cpu` (~300 MB) | CPU |

There are no Macs with NVIDIA that matter. The last ones were Intel Macs up to about 2014,
and Apple has not shipped NVIDIA drivers since 2018.

## Demo-State

1. **Windows with NVIDIA** (a real PC; CI has no GPU):
   - the ~70 MB `.exe` installs per user, with no admin rights;
   - the first start shows a setup screen: "NVIDIA GeForce … found — PyTorch with CUDA is
     being downloaded (2.5 GB)", with progress;
   - after it, the backend reports CUDA, and a head trains on the GPU.
2. **Interrupted:** unplug the network mid-download. The setup says so; with the network
   back, "Try again" continues where it stopped.
3. **Windows without NVIDIA:** the same installer sets up CPU (~300 MB).
4. **Mac with Apple Silicon:** it sets up MPS. **An Intel Mac:** "This Mac has an Intel
   processor; PyTorch no longer supports it" — before anything is downloaded.
5. **Admin → GPU:** switch CPU ⇄ GPU. The environment is re-synced, and the panel confirms
   the GPU is really used.
6. **An app update** (a new lock file) syncs only the changed packages before the backend
   starts. If the sync fails, the previous environment stays in use.
7. **CI:** on Windows, macOS and Linux runners, build, install silently, run setup (CPU),
   start the backend, check `/health`, and run one tiny inference. Installer and download
   sizes are recorded.

*(This wave is not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | dependency-lock | docs/125-dependency-lock.md | planned | — |
| 2 | bundled-python | docs/126-bundled-python.md | planned | dependency-lock |
| 3 | first-run-setup | docs/127-first-run-setup.md | planned | bundled-python |
| 4 | accelerator-switch | docs/128-accelerator-switch.md | planned | first-run-setup |
| 5 | update-sync | docs/129-update-sync.md | planned | first-run-setup |
| 6 | mac-distribution | docs/130-mac-distribution.md | planned | bundled-python, first-run-setup |
| 7 | installer-smoke-ci | docs/131-installer-smoke-ci.md | planned | bundled-python, first-run-setup, mac-distribution |

### Feature notes

1. **dependency-lock (125).**
   - One `uv.lock` for the backend, with hashes, and three variants: `cpu`, `cuda`
     (cu12x index) and `mac` (default wheels).
   - `pyproject.toml` declares the PyTorch indexes per variant (`[tool.uv.sources]`).
   - **CI checks** that the lock resolves on all three platforms, and runs the test suite
     from the locked environment, so the versions users get are the versions tested.
2. **bundled-python (126).**
   - The release build puts `python-build-standalone` (pinned version and checksum), the
     backend source and the `uv` binary into Tauri's resources. **No PyInstaller.**
   - Tauri gets `Launch::Bundled`: the bundled Python runs `-m app` against the environment
     in the user's app-data folder (`…/DinoTraining/env`), never in Program Files, so no
     admin rights are needed.
   - The Linux AppImage is tried again.
3. **first-run-setup (127).**
   - A setup screen in the Tauri window, before the backend exists, with plain words and a
     progress bar.
   - **Rust detects the machine:** OS, CPU architecture, `nvidia-smi` and the driver
     version. It chooses the variant; a CUDA driver too old for the locked CUDA version
     gets CPU, with the reason.
   - `uv sync --frozen` with that variant, its progress parsed and shown.
   - **Failures:**
     - offline: "No internet: the first start downloads PyTorch once";
     - interrupted: "Try again" continues;
     - disk space checked before starting.
   - An Intel Mac is refused before any download.
4. **accelerator-switch (128).**
   - Doc 57's panel gets the action it was missing: "Use the GPU (downloads ~2.5 GB)" /
     "Back to CPU".
   - It re-syncs the environment with the other variant, restarts the backend, and checks
     that the device is really used (doc 57's check).
   - It replaces doc 57's never-built CUDA sidecar download.
5. **update-sync (129).**
   - An app version carries its lock file. On start, if the environment's lock differs,
     `uv sync` runs, showing only what changed, into a fresh environment folder.
   - The old one is kept until the new one works, and removed after.
   - Tauri's own updater (the app shell) is **not** part of this wave: it needs signing.
6. **mac-distribution (130).** Verified before planning (2026-09-30):
   - **The quarantine test:** Wave 8's unsigned `.dmg`, fetched with the command line (no
     quarantine attribute) and copied out, **started without any warning**. Its binary is
     ad-hoc, linker-signed; `spctl` rejects it formally, but Gatekeeper only enforces on
     quarantined files. Only a **browser** download is blocked.
   - **Homebrew 7.0:** casks quarantine what they download (`cask/download.rb`); formulae
     do not (`formula_installer.rb` never mentions it). So:
     - **Release asset:** the CI builds the Tauri app for Apple Silicon and publishes it as
       `DinoTraining_<v>_aarch64.app.tar.gz` (no `.dmg`, which invites the browser).
     - **Homebrew:** a formula in a tap `JanderHungrige/homebrew-tap`:
       `brew install janderhungrige/tap/dinotraining`. It installs the app into the
       prefix and a `dinotraining` command.
     - **Script:** `scripts/install-mac.sh` for users without Homebrew, run with a
       one-line curl command. It refuses an Intel Mac, downloads and unpacks into
       `~/Applications`, and needs no admin rights.
     - **"Add to Applications":** a formula may not write outside its prefix, so on the
       first start from the prefix the app offers to link itself into `~/Applications`.
     - **Updates:** `brew upgrade`, or the script again.
     - **The README** says why not to download in the browser, and the one-time "Open
       anyway" (Privacy & Security) for anyone who did.
   - **Creating the public tap repository** is publishing: Jan creates it, or approves
     it, when the formula is ready.
7. **installer-smoke-ci (131).**
   - The release workflow gains a smoke job per platform:
     - install silently (NSIS `/S`, mount the dmg, `dpkg -i`);
     - run setup headless (CPU; the runners have no GPU);
     - start, check `/health`, run a tiny inference;
     - uninstall.
   - It records the installer size and the download size.

## Open questions (for Jan, before or during the build)

- [x] **Code signing:** none paid (Jan, 2026-09-30).
  - macOS: installed without quarantine, see feature 6.
  - Windows: unsigned, so SmartScreen shows "Run anyway". The free SignPath Foundation
    signing for open-source projects may come later.
- [ ] **A real Windows PC with an NVIDIA card** for demo steps 1–2; CI cannot test the GPU.
- [ ] **CUDA version:** cu126 (older drivers) or cu128 (newest cards, e.g. RTX 50xx need
  it)? Proposal: choose by the driver version detected, and lock both.

## Open Research

- **`uv sync` progress:** is its output parseable enough for a progress bar, or does the
  setup count downloaded bytes of the cache itself?
- **Size:** does `python-build-standalone` together with the app source stay under 80 MB
  compressed on Windows?
- **NVIDIA libraries on Windows:** do the pip `nvidia-*` packages load without a system CUDA
  install? (They should: that is what the cu12x wheels rely on.) Verify in CI on a
  Windows runner without a GPU, by importing only.

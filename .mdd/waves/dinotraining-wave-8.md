---
id: dinotraining-wave-8
title: "Wave 8: Packaging & Distribution"
initiative: dinotraining
initiative_version: 5
status: complete
closed: 2026-08-21
deferred: [code-signing-notarization, auto-update, first-run-model-bootstrap]
depends_on: dinotraining-wave-7
demo_state: "A new user installs a signed macOS/Windows/Linux installer; on first run it downloads required weights via the admin tab and the full annotate→train→infer loop works."
created: 2026-08-14
hash: 9ff056cc
---

# Wave 8: Packaging & Distribution

## Demo-State

DinoTraining ships as an installable, sharable app. A user downloads a signed installer
(`.dmg` / `.msi` / `.AppImage`), installs it, and on first run the admin tab bootstraps the
required model weights (kept out of the installer so it stays small). The full
annotate → train → infer → generate loop works from the installed app.
*(Not complete until this can be manually demonstrated.)*

## Closed 2026-08-21 — four of seven, and what the other three need

Closed on Jan's call with three features deferred. Recording them as deferred rather than
done, because the wave's demo-state says *"installs a **signed** installer"* and nothing is
signed.

**Shipped**

| | | |
|---|---|---|
| 1 | python-sidecar-bundling | doc 56 — PyInstaller freezes the FastAPI+torch sidecar; 636 MB, and it runs |
| 2 | tauri-installers | doc 58 — Windows 181 MB, macOS 311 MB, Linux 377 MB |
| 3b | gpu-support-download | doc 57 — detection, reporting and the Rust preference order |
| 5 | release-ci | doc 58 — green on all three platforms, run 4 |

Plus two the wave never asked for and needed anyway: doc 54 (what shipping obliges) and
doc 59 (open a dataset's folder).

**Deferred, with reasons**

- **4 — code signing and notarization.** Needs Apple and Windows certificates, which are
  Jan's to hold and cannot be handled here. Until it exists, the macOS build is
  Gatekeeper-blocked on first launch and the Windows one gets a SmartScreen warning. The
  release job already creates a **draft** rather than publishing, precisely so an unsigned
  build cannot reach anyone by accident.
- **6 — auto-update.** Depends on 4: an updater that installs unsigned payloads is worse
  than no updater. It also needs a real answer to size — a 292 MB download per patch is a
  bad citizen and Tauri's updater does not diff.
- **3 — first-run model bootstrap.** Arguably already covered: the Admin tab downloads on
  demand (doc 02), the Intro tab explains the loop (doc 38), and doc 57 handles
  accelerators. What does not exist is a *guided* first run, and **nobody has ever
  installed this app from an installer onto a clean machine** — only the macOS `.app` was
  launched, from its own build directory. That is the honest gap.

## Demo-state, as far as it got

*"A new user installs a signed installer; on first run it downloads required weights via
the admin tab and the full loop works."*

Demonstrated: the **macOS `.app`, launched from the bundle**, started its own sidecar from
`Contents/Resources/sidecar` and served a real RF-DETR inference — 25 boxes in 88 ms — with
no Python, no venv and no checkout. Windows and Linux **build** but have never been
installed or launched.

Not demonstrated: *signed*, and *a new user on a clean machine*.

## Confirmed by Jan, 2026-08-21

**GPU: CPU-only by default, CUDA as a download.** Chosen over shipping CUDA everywhere (a
2.5 GB Windows installer) and over CPU-only everywhere (which would cost NVIDIA users the
acceleration a *training* app most needs). Doc 57 builds the detection, the reporting and
the Rust preference order; the artefact itself waits on `release-ci`, because a download
cannot exist before there is something publishing it.


**All three platforms are required, not a choice between them.** macOS, Windows and Linux
each get an installer. The demo-state above already said so; this records that it is a
requirement rather than an aspiration, which matters because it decides the CI shape — the
sidecar has to be built on each platform (PyInstaller does not cross-compile, and the torch
wheel differs per platform), so feature 5 needs a build matrix rather than one runner.

**Doc 54 is a prerequisite for feature 5, not a nicety.** The Admin panel now names which
installed models carry a licence obligation, but it is only a *notice*. A release build that
happens to run on a machine with SAM 3 in its cache must not pick it up. The release job
needs to either build against an empty cache or fail loudly when a restricted model is
present — the notice helps a human who reads it, and CI does not read.

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | python-sidecar-bundling | **56** | **spiked — works, 636 MB** | — |
| 2 | tauri-installers | **58** | **all three build; only macOS launched** | 56 |
| 3 | first-run-model-bootstrap | — | **deferred** | — |
| 3b | **gpu-support-download** | **57** | **detection done; artefact pending release-ci** | 56 |
| 4 | code-signing-notarization | — | **deferred — needs Jan's certificates** | 2 |
| 5 | release-ci | **58** | **green on all three, run 4** | 2, 54 |
| 6 | auto-update | — | **deferred** | 5, 4 |

### Feature notes

- Bundle the FastAPI+PyTorch sidecar as a Tauri external binary per-platform. **Spiked on
  2026-08-21 — doc 56.** PyInstaller works and the frozen build serves real inferences.
  It is **636 MB**, and the torch wheel variant makes a Windows CUDA build 2.5 GB before
  anything else. That is a product decision waiting on Jan, not a build detail.
- Tauri build → platform installers; keep installer small (no weights bundled).
- First-run flow that guides model download + HF token for gated DINOv3.
- macOS notarization + Windows signing (open product question).
- **Linux has no signing step** in the same sense; AppImage is unsigned and distribution
  is by checksum. Worth stating so it is not mistaken for an oversight.
- GitHub Actions matrix build producing installers as release artifacts.
- Optional auto-update (Tauri updater).

## Open Research

- Size/feasibility of a bundled PyTorch runtime per platform; CPU-only vs. CUDA variants.
- Signing certificates and notarization cost/process.

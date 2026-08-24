---
id: dinotraining-wave-8
title: "Wave 8: Packaging & Distribution"
initiative: dinotraining
initiative_version: 5
status: planned
depends_on: dinotraining-wave-7
demo_state: "A new user installs a signed macOS/Windows/Linux installer; on first run it downloads required weights via the admin tab and the full annotate→train→infer loop works."
created: 2026-08-14
hash: c7739468
---

# Wave 8: Packaging & Distribution

## Demo-State

DinoTraining ships as an installable, sharable app. A user downloads a signed installer
(`.dmg` / `.msi` / `.AppImage`), installs it, and on first run the admin tab bootstraps the
required model weights (kept out of the installer so it stays small). The full
annotate → train → infer → generate loop works from the installed app.
*(Not complete until this can be manually demonstrated.)*

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
| 3 | first-run-model-bootstrap | — | planned | — |
| 3b | **gpu-support-download** | **57** | **detection done; artefact pending release-ci** | 56 |
| 4 | code-signing-notarization | — | planned | tauri-installers |
| 5 | release-ci | **58** | **green on all three, run 4** | 2, 54 |
| 6 | auto-update | — | planned | release-ci |

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

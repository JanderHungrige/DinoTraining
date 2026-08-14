---
id: dinotraining-wave-5
title: "Wave 5: Packaging & Distribution"
initiative: dinotraining
initiative_version: 1
status: planned
depends_on: dinotraining-wave-4
demo_state: "A new user installs a signed macOS/Windows/Linux installer; on first run it downloads required weights via the admin tab and the full annotate→train→infer loop works."
created: 2026-08-14
hash: 332f2716
---

# Wave 5: Packaging & Distribution

## Demo-State

DinoTraining ships as an installable, sharable app. A user downloads a signed installer
(`.dmg` / `.msi` / `.AppImage`), installs it, and on first run the admin tab bootstraps the
required model weights (kept out of the installer so it stays small). The full
annotate → train → infer → generate loop works from the installed app.
*(Not complete until this can be manually demonstrated.)*

## Features (draft — refined in plan-wave)

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | python-sidecar-bundling | — | planned | — |
| 2 | tauri-installers | — | planned | python-sidecar-bundling |
| 3 | first-run-model-bootstrap | — | planned | — |
| 4 | code-signing-notarization | — | planned | tauri-installers |
| 5 | release-ci | — | planned | tauri-installers |
| 6 | auto-update | — | planned | release-ci |

### Feature notes

- Bundle the FastAPI+PyTorch sidecar (PyInstaller / embedded env) as a Tauri external binary
  per-platform. Spike this in Wave 1 since it constrains everything.
- Tauri build → platform installers; keep installer small (no weights bundled).
- First-run flow that guides model download + HF token for gated DINOv3.
- macOS notarization + Windows signing (open product question).
- GitHub Actions matrix build producing installers as release artifacts.
- Optional auto-update (Tauri updater).

## Open Research

- Size/feasibility of a bundled PyTorch runtime per platform; CPU-only vs. CUDA variants.
- Signing certificates and notarization cost/process.

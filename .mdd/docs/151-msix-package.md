---
id: 151-msix-package
title: MSIX Package — The Store Edition Packed From the Same Windows Build as the EXE
edition: DinoTraining
depends_on: [126-bundled-python, 134-app-emblem]
relates: [152-msix-runtime, 153-msix-smoke-ci, 155-store-submission]
source_files:
  - packaging/msix/AppxManifest.template.xml
  - packaging/msix/identity.json
  - scripts/stage_msix.py
  - .github/workflows/release.yml
  - .github/workflows/lock-check.yml
routes: []
models: []
test_files:
  - scripts/test_stage_msix.py
data_flow: greenfield
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [msix, microsoft-store, windows, packaging, release, ci]
path: Installer/Windows/MSIX
initiative: dinotraining
wave: dinotraining-wave-15-10
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 151 — MSIX Package

## Purpose

- **Wave 15.10:** the Microsoft Store signs MSIX packages for free.
- **This doc packs one from the release's Windows build**, beside the NSIS installer,
  which stays as it is.

## What goes in (`scripts/stage_msix.py`)

- **`DinoTraining.exe`:** the release build's `target/release/dinotraining.exe`.
- **`runtime/`:** doc 126's staged backend source, lock and uv, as the NSIS installer
  carries them.
  - The app finds them beside its exe (`Runtime::find`) and puts the environments into
    `%LOCALAPPDATA%\DinoTraining\runtime`, as it does now.
  - Microsoft's Tauri guide stages only the exe, and this app would not start without
    these files.
- **`Assets/`:** the Store logos `tauri icon` made from the emblem (doc 134):
  `Square44x44Logo.png`, `Square150x150Logo.png`, `StoreLogo.png`.
- **`AppxManifest.xml`,** written from `packaging/msix/AppxManifest.template.xml`:
  - **Identity:** `Identity Name` and `Publisher` from `packaging/msix/identity.json`.
    - These are **placeholders until Jan has reserved the name** in Partner Center. They
      are then replaced with what Partner Center shows, a change of one file.
  - **Version:** the app's `0.1.3` becomes `0.1.3.0`; the Store requires the fourth part
    to be 0.
  - **The application:** one full-trust desktop entry
    (`EntryPoint="Windows.FullTrustApplication"`).
  - **Capabilities:** `internetClient` and `runFullTrust`.
  - **Target:** `Windows.Desktop` from 10.0.17763.0 (Windows 10 1809), x64.
  - **Languages:** English and German.
- **The script refuses** a version that is not three numbers, a missing exe, runtime or
  logo, and an identity still empty. A placeholder identity is allowed and is said in
  the output.

## Packed and signed in the release workflow (Windows job)

- **`makeappx pack`** from the Windows SDK on the runner →
  `DinoTraining_<version>_x64.msix`, **unsigned: what the Store takes** (Microsoft signs
  it).
- **A copy signed with a self-signed test certificate** whose subject is the manifest's
  `Publisher`: `DinoTraining_<version>_x64_test.msix` with its `.cer`.
  - It is for doc 153's smoke test and for Jan's PCs (the certificate must be trusted
    first).
  - It is a workflow artifact only, never a release download: a user would have to trust
    a certificate, which is exactly what the Store avoids.
- **The release** (doc 131's publish job) carries the unsigned `.msix` beside the EXE, for
  doc 155's submission.
- **The job summary** shows both sizes.

## Tests

- `scripts/test_stage_msix.py`, run by `lock-check.yml` with the other script tests:
  - staging copies exactly the exe, the runtime tree and the three logos;
  - the manifest carries the identity, `x.y.z.0`, the capabilities and the entry point,
    and is well-formed XML;
  - each refusal.
- **The release dry run** packs and signs on a real Windows runner.

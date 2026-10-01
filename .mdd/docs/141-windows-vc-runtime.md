---
id: 141-windows-vc-runtime
title: Windows VC++ Runtime — PyTorch Needs MSVCP140 14.40 or Newer; Setup Checks and Installs It
edition: DinoTraining
depends_on: [127-first-run-setup, 139-backend-streams]
relates: [131-installer-smoke-ci, 132-uninstall]
source_files:
  - apps/desktop/src-tauri/src/vc_runtime.rs
  - apps/desktop/src-tauri/src/vc_runtime.ps1
  - apps/desktop/src-tauri/src/setup_flow.rs
  - apps/desktop/src-tauri/src/setup.rs
  - apps/desktop/src-tauri/src/progress.rs
  - apps/desktop/src-tauri/src/backend_log.rs
  - apps/frontend/src/setup/shell.ts
  - apps/frontend/src/setup/SetupScreen.tsx
  - apps/frontend/src/setup/SetupFailureNotice.tsx
  - apps/frontend/src/i18n/en/setup.ts
  - apps/frontend/src/i18n/de/setup.ts
  - .github/workflows/lock-check.yml
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/vc_runtime.rs
  - apps/frontend/src/setup/SetupFailureNotice.test.tsx
data_flow: greenfield
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [installer, windows, msvc, vc-redist, pytorch, setup, dll]
path: Installer/Windows/VC Runtime
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites:
  - apps/desktop/src-tauri/src/vc_runtime.ps1 (runs a downloaded installer elevated; only after its Authenticode signature is valid and Microsoft's)
sister_projects: []
---

# 141 — The Windows VC++ Runtime

## What happened (Jan, second Windows PC, no NVIDIA, release 0.1.1)

- **The CPU setup ran through; the backend died on `import torch`:**
  `OSError: [WinError 1114] Eine DLL-Initialisierungsroutine ist fehlgeschlagen. Error
  loading "…\torch\lib\c10.dll" or one of its dependencies.` Doc 139 made this
  visible; before it, there was no log at all.
- **The machine's `msvcp140.dll` is 14.28.29334** (VS 2019 era).
- **The NVIDIA PC works**: it has a newer runtime, as most machines with current
  drivers or games do.

## Why

- **PyTorch 2.13's Windows wheels do not ship the C++ runtime.** Checked in the
  wheels themselves:
  - `c10.dll` imports `MSVCP140.dll`, `VCRUNTIME140.dll` and `VCRUNTIME140_1.dll`;
  - `torch/lib` carries none of them, in the `cpu` wheel or the `cu130` one.
  - The process uses whatever Windows has.
- **Built with MSVC 14.40 or newer**, the DLL's initialisation fails against an older
  `msvcp140.dll` (the STL's mutex changed in VS 17.10). Hence 1114, not "not found".
- **CI is blind to it:** GitHub's Windows runners have Visual Studio, and with it the
  newest runtime.

## The fix

1. **Checked before every setup, on Windows only** (`vc_runtime.rs`):
   - **The version comes from the registry** (`HKLM\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64`,
     `Version`, through `reg query … /reg:64`). This is what the official redistributable
     writes.
   - **Missing, unreadable or older than 14.40 counts as "needs the runtime".**
     Installing over a newer one is harmless (exit code 1638).
2. **Installed by the setup, before PyTorch** (`vc_runtime.ps1`, run by PowerShell):
   - downloads Microsoft's permanent link `https://aka.ms/vs/17/release/vc_redist.x64.exe`;
   - **refuses it unless its Authenticode signature is valid and Microsoft's**;
   - runs it with `/install /passive /norestart`, elevated: **Windows asks for
     permission once**, and Microsoft's own progress window shows.
   - Success is exit 0, 3010 (a restart is suggested, not needed for this) or 1638
     (already newer). The version is read again afterwards.
   - The setup screen says what is happening: "Installing the Microsoft Visual C++
     runtime — Windows will ask for permission."
3. **An installed app with an old runtime goes back through the setup.**
   - `needs_setup` is true when the runtime is too old, even with a ready environment.
     That was Jan's state: the environment was installed and only the backend failed.
   - The screen takes the existing variant (as an update, doc 129), installs the
     runtime and checks the environment again, which comes from uv's cache in seconds.
4. **Refused or failed:** a failure of its own kind (`vc_runtime`) with the version found
   and Microsoft's link, so the user can install it by hand and press "Try again":
   - the permission prompt was declined;
   - the download or the signature failed;
   - the installer reported an error.
5. **The backend error says it, too.** If a start fails and the log shows `c10.dll` with
   WinError 1114 or 126, the message adds the hint and the link. That covers a runtime
   removed after setup.

## Tests

- **Rust:**
  - parsing `reg query`'s output;
  - comparing versions;
  - the installer's exit codes;
  - the hint for the backend log.
- **Frontend:** the failure's wording (EN/DE); the new phase.
- **CI (`lock-check.yml`, Windows):** the script runs for real on the runner.
  - It checks the download, the signature and the elevated start; the runner already
    has a newer runtime, so the exit code is 0 or 1638.
  - It does not reproduce an old runtime. That needs Jan's second PC.

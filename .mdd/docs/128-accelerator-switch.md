---
id: 128-accelerator-switch
title: Accelerator Switch — CPU ⇄ GPU from the Admin Tab, with Rollback and a Device Check
edition: DinoTraining
depends_on: [127-first-run-setup, 126-bundled-python, 57-gpu-detection]
relates: [129-update-sync]
source_files:
  - apps/desktop/src-tauri/src/setup_flow.rs
  - apps/desktop/src-tauri/src/switch.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/frontend/src/components/GpuPanel.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/setup/SetupScreen.tsx
  - apps/frontend/src/setup/shell.ts
  - apps/frontend/src/setup/SwitchOverlay.tsx
  - apps/frontend/src/setup/SetupFailureNotice.tsx
  - apps/frontend/src/setup/setup.css
  - apps/desktop/src-tauri/src/setup.rs
  - apps/frontend/src/i18n/en/admin.ts
  - apps/frontend/src/i18n/de/admin.ts
  - apps/frontend/src/i18n/en/setup.ts
  - apps/frontend/src/i18n/de/setup.ts
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/switch.rs (unit tests)
  - apps/frontend/src/components/GpuPanel.test.tsx
  - apps/frontend/src/setup/SetupScreen.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [installer, gpu, cuda, uv, admin, tauri]
path: Installer/AcceleratorSwitch
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The switch itself (stop, uv sync to another variant, restart, rollback) was not run live: this Mac has only the one variant, and GitHub's runners have no GPU. Verified by unit tests (the rollback rule, the failure shape, every panel state, the screen's switch mode) and live for its parts (install, start, the port wait). First real run: a Windows or Linux machine with an NVIDIA card."
security_read_sites: []
sister_projects: []
---

# 128 — Accelerator Switch

## Purpose

- **Doc 57's panel** says "your GPU is not being used" and offered a CUDA sidecar
  download that was never built. Doc 126 removed that sidecar.
- **Now:** the panel switches the installed PyTorch between CPU and GPU. It is the same
  `uv sync` as the first start (doc 127), with another extra.
- **Who needs it:** someone who picked "CPU only" at the first start; someone who
  updated their NVIDIA driver since; someone whose GPU build misbehaves and who wants
  the CPU back.

## What the panel shows (Admin tab)

| State | Panel |
|---|---|
| Not the packaged app (development, browser) | doc 57 as before: the note, no button (a developer installs the CUDA extra with uv) |
| Packaged, CPU installed, the machine can take a CUDA build | "Your GPU is not being used" + **Use the GPU (CUDA 13.0, about 3,5 GB download)** |
| Packaged, CUDA installed and the backend runs on `cuda` | one line: "GPU in use (CUDA 13.0)" + **Back to CPU** |
| Packaged, CUDA installed but the backend runs on `cpu` | a warning: the GPU build is installed but not used, the backend's summary, and **Back to CPU** |
| Driver installed but not answering | doc 57's driver notice |
| Driver too old for CUDA (doc 127's note) | the note, no button |
| Mac, no NVIDIA | nothing (MPS is always included) |

## The switch (Rust, `switch_variant(variant)`)

1. The variant must be one of this machine's choices (doc 127).
2. Disk space, then the connection (doc 127's checks).
3. **Stop the backend**: running jobs end. The button says so before it starts.
4. `uv sync --frozen --extra <variant>` with progress events (doc 127's parser).
5. **Start the backend** and wait for `/health`, as the first start does.
6. **When 4 or 5 fails:** sync the previous variant back. It comes from uv's cache, so
   this works offline. Then restart and report "Switching failed: …; you are back on
   the CPU." The app is never left without a working environment.

- **The port:** a just-stopped backend can leave the port briefly unbindable. The
  startup waits up to 5 s for it to free, instead of failing at once.
- **`runtime_status`:** the installed variant (`installed.json`, doc 126) and the
  machine's choices, for the panel.

## The screen during the switch

- The setup screen (doc 127), full-window over the app, with this variant already
  chosen: progress, Dino Run, tips. Its title and intro say "Switching to the GPU" or
  "Switching to the CPU".
- **When the backend answers**, the overlay closes and the Admin tab re-reads the
  accelerator. **The device check** (doc 57): a GPU build whose backend still reports
  `cpu` shows the warning row above.

## Verified (2026-10-01)

- **Rust (5 new unit tests, 20 in all):** a failed switch goes back to what was
  installed, or to the CPU when that is unknown; nothing to go back to when the switch
  was to the same variant; an unknown previous variant is not invented; the
  `rolled_back` failure carries where it went and why, nested.
- **Frontend:**
  - the panel (13 tests): nothing without NVIDIA, on a Mac, or before the report; a
    checkout says how to install the GPU build, with no button; the packaged app on the
    CPU offers "Use the GPU (CUDA 13.0, about 3.5 GB download)" and switches to `cu130`;
    on the GPU and using it, one line and "Back to CPU"; the GPU build installed but the
    backend on the CPU, the warning with the backend's reason (doc 57's check); a driver
    too old, the reason and no button; the driver not answering, doc 57's notice;
  - the screen (2 new tests): a switch runs its own command under "Switching to the GPU"
    without a click; a rolled-back switch says "Switching did not work: No internet
    connection. You are back on the CPU, as before." and "Back to the app" closes it;
  - the whole suite: 1121 passed.
- **The release app, live:**
  - a normal start with an installed runtime is healthy in 6 s;
  - with the port taken (the dev backend on 8756), the start waits 5 s, then reports
    "port 8756 is already in use" as before.

---
id: 129-update-sync
title: Update Sync — A New Lock Builds a Fresh Environment Beside the Old; the Old Stays Until the New Works
edition: DinoTraining
depends_on: [126-bundled-python, 127-first-run-setup, 128-accelerator-switch]
relates: [131-installer-smoke-ci]
source_files:
  - apps/desktop/src-tauri/src/runtime.rs
  - apps/desktop/src-tauri/src/uv_sync.rs
  - apps/desktop/src-tauri/src/setup_flow.rs
  - apps/desktop/src-tauri/src/switch.rs
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/frontend/src/setup/SetupGate.tsx
  - apps/frontend/src/setup/SetupScreen.tsx
  - apps/frontend/src/setup/SetupFailureNotice.tsx
  - apps/frontend/src/setup/shell.ts
  - apps/frontend/src/i18n/en/setup.ts
  - apps/frontend/src/i18n/de/setup.ts
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/runtime.rs (unit tests)
  - apps/desktop/src-tauri/src/switch.rs (unit tests)
  - apps/frontend/src/setup/SetupScreen.test.tsx
  - apps/frontend/src/setup/SetupGate.test.tsx
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [installer, update, uv, lockfile, rollback, tauri]
path: Installer/UpdateSync
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "'Start with the previous packages' (start_previous) was verified by unit tests only: it needs a click, and this session could not click into the app window."
security_read_sites: []
sister_projects: []
---

# 129 — Update Sync

## Purpose

- **An app version carries its lock** (doc 125). A new version with a changed lock needs
  the packages it was tested with, so the environment is synced on its first start.
- **An update must never brick the app.** Offline right after an update, a failed
  download or a new build that does not start: the previous environment is still there
  and still starts.
- The Tauri updater (the app itself) is not part of this wave: it needs signing.

## Environments side by side (replaces doc 126's single `env/`)

```
runtime/
  python/  cache/
  envs/<id>/        one folder per sync; <id> is the time it was made (ms)
    installed.lock  the lock it was synced from
    installed.json  {variant, installed_at}
  current           the id of the environment the backend runs in
```

- **Every sync builds a new folder.** The running one is never touched, so the backend
  can keep running while it downloads (doc 128's switch), and a failed sync leaves
  nothing half-installed behind.
- **`current` is switched in one step** (written to a temporary file, then renamed).
- **Cleanup:** once the backend answers on the new environment, every other folder in
  `envs/` is removed. Leftovers of an interrupted sync go the same way at the next
  successful switch.
- **Disk:** uv links files from its cache instead of copying them (clones on macOS,
  hard links on Windows and Linux), so two environments side by side cost little.
- **Ready** means that `current` names a folder with a Python, and that its
  `installed.lock` is byte for byte the bundled lock (doc 126's rule, per folder).

## The update (first start of a new version)

1. **The setup screen** (doc 127) sees an existing but outdated environment: it updates
   at once, with the installed variant and no question. Its title is "Updating
   DinoTraining's packages", and uv only downloads what changed.
2. **Success:** the shell switches `current`, starts the backend and removes the old
   folder.
3. **Failure** (offline, a failed sync, a backend that does not start on the new
   packages):
   - the screen says why, and offers **Try again** and **Start with the previous
     packages**;
   - the second starts the backend on the old folder. The new app code may need a
     changed package, so the screen says the update is still pending; the next start
     tries again.

## Doc 128's switch, on the same footing

- `uv sync` builds the new variant in a new folder **while the backend keeps running**.
- Only then: stop the backend, switch `current`, start, and wait for `/health`.
- **The new build does not start:** switch `current` back and start the old one:
  seconds, nothing downloaded. Reported as "back on the CPU, as before".
- **The sync fails:** nothing was stopped or switched. The screen says why, and "Back to
  the app" returns to a backend that never went away.

## Verified (2026-10-01)

- **Rust (runtime, 6 tests):**
  - ready only with a current environment from the same lock;
  - a new lock is not ready, but the old environment stays usable;
  - a new build does not switch by itself; activating switches, and cleanup keeps only
    the current one (including an interrupted sync's leftover);
  - a pointer to a missing folder is no environment;
  - a new environment never reuses an existing folder;
  - uv stays isolated.
- **Frontend (3 new tests):** an update runs without a question under "Updating
  DinoTraining's packages"; a failed update offers "Start with the previous packages",
  which starts it and opens the app; a first install offers no such thing. The whole
  suite: 1124 passed.
- **The release app, live, one runtime folder through four starts:**
  1. **First start:** one environment, current, healthy (57 s).
  2. **Simulated app update** (the bundled lock changed): the screen updated by itself.
     uv downloaded nothing and installed 68 packages from its cache in 0.4 s; the new
     environment became current, the backend answered, and the old one was removed.
     Total: 33 s, almost all of it the backend's first import.
  3. **A failing update** (a broken lock): "Setup screen: failed" after 2 s; `current`
     unchanged; the old environment intact with its Python; the backend not started.
  4. **The next good update:** switched, and removed both the replaced environment and
     the failed attempt's leftover folder.
- **Doc 128's switch uses the same footing:** the backend keeps running while the new
  variant downloads, and a rollback points back instead of re-syncing.

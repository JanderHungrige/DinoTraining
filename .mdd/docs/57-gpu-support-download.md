---
id: 57-gpu-support-download
title: GPU Support as a Download — CPU by Default, CUDA on Request
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-8
wave_status: in_progress
depends_on: [56-sidecar-bundling]
relates: [02-model-download-manager, 35-model-licence-surfacing]
source_files:
  - backend/app/ml/accelerator.py
  - backend/app/api/v1/system.py
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/desktop/src-tauri/BUNDLING.md
  - apps/desktop/src-tauri/tauri.release.conf.json
  - apps/frontend/src/api/models.ts
  - apps/frontend/src/components/GpuPanel.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/system/accelerator
models: []
test_files:
  - backend/tests/test_accelerator.py
  - apps/frontend/src/components/GpuPanel.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [packaging, gpu, cuda, nvidia, sidecar, admin, detection]
path: Admin / Models/GPU
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - backend/app/ml/accelerator.py (runs nvidia-smi from PATH; fixed argv, no shell, 5s timeout)
known_issues:
  - "**The download itself is not built.** Detection, reporting, the panel and the Rust preference order are done and tested; what is missing is the artefact to download and the job that fetches it, because neither can exist before there is a release pipeline. `GpuPanel` renders without a button when no handler is passed, which is the current state — it still tells the user their GPU is idle, which is the more important half."
  - "**`CUDA_SIDECAR_MB` is a hard-coded 2400.** It is a property of a release, not of the running app, and the app cannot know it before asking. It must be updated alongside the first release that publishes one."
  - "**Verified with a simulated driver**, not real NVIDIA hardware — this is a Mac. A fake `nvidia-smi` on PATH exercised the whole path including the UI, but the CUDA sidecar has never been built or run."
  - "`nvidia-smi` is trusted to mean \"a usable GPU\". A machine where it answers but CUDA is nonetheless unusable (mismatched driver/runtime versions) would be offered a download that does not help."
  - "Only NVIDIA. ROCm is detected as a torch variant but never offered, and Intel/Arc is not considered at all."
sister_projects: []
---

# 57 — GPU Support as a Download

## The decision

Doc 56 measured the problem: a CUDA torch wheel is **2532 MB on Windows** against 111 MB
for CPU-only, and `resolve_device` picks CUDA → MPS → CPU, so the app supports NVIDIA
today. Jan chose **CPU by default, GPU as a download** — the option that forces no loss and
matches what this app already does with model weights.

## Why it cannot be a pip install

The obvious implementation is wrong and worth writing down. "Download the GPU parts" sounds
like `pip install torch --index-url .../cu124`, and that is impossible here: the sidecar is
a **frozen binary** (doc 56) with torch baked into `_internal`. There is no environment to
install into.

CPU torch and CUDA torch are also not the same package with an add-on. They are different
builds of the same module, and the CUDA one carries NVIDIA's runtime libraries — which is
where the 2.4 GB actually goes.

So GPU support is **a second frozen sidecar**, downloaded whole and preferred when present.
That is more bytes than a pip install would move, and it is the only version that works
offline, cannot half-succeed, and needs no Python toolchain on the user's machine. It is
also the shape this app already has for weights: a verified artefact fetched into the data
directory, with the Admin tab as the place it happens.

## Three questions the app used to conflate

`accelerator.py` exists because **torch cannot answer "is there a GPU here"**. A CPU-only
build reports `torch.cuda.is_available() == False` on a machine with four A100s.

| question | answered by |
|---|---|
| Is there NVIDIA hardware with a working driver? | `nvidia-smi` — ships with the driver, answers on any torch build |
| Can *this build* use it? | `torch.version.cuda` — a property of the frozen wheel |
| What is being used right now? | `resolve_device`, which already existed |

Only the combination **hardware yes, build no** is actionable, and it is the only state the
panel renders in. Not "no GPU found" (most machines, and standing noise), not "CUDA working"
(nothing to do). A panel that is always there is one nobody reads.

A fourth state earns its own message: **the driver is installed and did not answer.** That
is a different problem from having no GPU and needs a different fix, so it must not collapse
into the same silence.

## Business Rules

1. **`is_built`, not `is_available`, for the torch variant.** It reports what the *wheel*
   can do. The macOS wheel is MPS-capable whether or not a particular Mac has a usable GPU,
   and calling that build `cpu` would tell a user on Apple silicon they lack acceleration
   they already have.
2. **The probe never raises.** It is decoration on the Admin panel, and a probe that threw
   on an unusual machine would take the panel down with it. A timeout, a missing binary and
   a non-zero exit are three different answers, none of them an exception.
3. **A malformed `nvidia-smi` line is skipped, not fatal.** A machine with one odd GPU among
   four should report the three that parsed.
4. **The downloaded GPU sidecar wins over the bundled one.** That is the point of
   downloading it; a flag the user must find means someone runs on CPU for a week without
   noticing.
5. **It lands in the data directory, not beside the executable.** Installed application
   directories are read-only on macOS and need elevation on Windows.
6. **The panel says why the installer did not include it.** Without that sentence, 2.4 GB
   reads as the app being bloated rather than as CUDA being big.

## One thing that broke, and how it is fixed

Adding `externalBin` to `tauri.conf.json` makes Tauri's build script fail when the binary is
absent — so `cargo check` and `npm run tauri dev` stopped working for anyone who had not
first built a 640 MB sidecar. Development does not need one.

The sidecar now lives in `tauri.release.conf.json`, merged in only for release builds. See
`apps/desktop/src-tauri/BUNDLING.md`.

## Verified

19 backend tests and 11 frontend. **Verified in the running app on 2026-08-21** with a fake
`nvidia-smi` on PATH standing in for a driver, since this is a Mac:

```
simulated   "NVIDIA GeForce RTX 4090, 24564, 550.54.14"
API         upgrade_available: true
            "NVIDIA GeForce RTX 4090 found, but this build runs on mps."
panel       ⚡ Your GPU is not being used — RTX 4090 · 24 GB · driver 550.54.14
real Mac    upgrade_available: false, panel absent
```

`cargo check` clean on the Rust preference order.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

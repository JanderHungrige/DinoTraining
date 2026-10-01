---
id: 130-mac-distribution
title: Mac Distribution — Unsigned but Unquarantined, via an Install Script or a Homebrew Formula
edition: DinoTraining
depends_on: [126-bundled-python, 127-first-run-setup, 58-installers]
relates: [131-installer-smoke-ci]
source_files:
  - .github/workflows/release.yml
  - .github/workflows/lock-check.yml
  - apps/frontend/src/look.css
  - scripts/install-mac.sh
  - scripts/render_formula.py
  - packaging/homebrew/dinotraining.rb.template
  - apps/desktop/src-tauri/src/mac_apps.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/frontend/src/components/AddToApplications.tsx
  - apps/frontend/src/App.tsx
  - README.md
routes: []
models: []
test_files:
  - scripts/test_install_mac.sh
  - scripts/test_render_formula.py
  - apps/desktop/src-tauri/src/mac_apps.rs (unit tests)
  - apps/frontend/src/components/AddToApplications.test.tsx
data_flow: greenfield
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [installer, macos, homebrew, gatekeeper, quarantine, release]
path: Installer/Mac
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The formula could not be installed on this Mac: Homebrew refuses every install while the Command Line Tools are outdated, and updating them needs sudo. Verified instead: brew style (no offenses), ruby -c, the formula's exact layout run by hand, and the app it installs. First real install: when Jan publishes the tap."
  - "Not published: the tap repository JanderHungrige/homebrew-tap does not exist yet. Jan creates it and copies in the dinotraining.rb the release attaches."
  - "The Add button itself (the symbolic link) was not clicked live: no permission to click into the window. The offer was verified live; the link is two std calls, and the frontend is unit-tested."
  - "Spotlight may not list an app that is only a symbolic link in ~/Applications; Finder, the Dock and open -a do. The script install is a real folder and has no such limit."
security_read_sites: []
sister_projects: []
---

# 130 — Mac Distribution

## Purpose

- **No paid signing** (Jan: no 100 € a year to Apple for an open-source project).
- **Measured before planning (2026-09-30):**
  - Gatekeeper enforces only on files carrying the quarantine attribute. A browser sets
    it; `curl` and Homebrew *formulae* do not. Homebrew *casks* do.
  - Wave 8's unsigned app, fetched with `curl` and copied out, started without a
    warning.
- **So the Mac gets two ways in, both from the command line:** a script and a Homebrew
  formula. Neither needs admin rights or a warning dialog.
- **Still Tauri, not a browser page:** folder pickers need the native dialogs (Jan).

## The release asset

- The release workflow's macOS leg builds `--bundles app` and packs it as
  `DinoTraining_<version>_aarch64.app.tar.gz`, with a `.sha256` beside it.
- **No `.dmg`:** a disk image invites a browser download, which is exactly the path
  Gatekeeper blocks.
- The same leg renders the Homebrew formula for that version and checksum
  (`scripts/render_formula.py`) and attaches it to the release as `dinotraining.rb`.

## The script — `scripts/install-mac.sh`

```
bash -c "$(curl -fsSL https://raw.githubusercontent.com/JanderHungrige/DinoTraining/main/scripts/install-mac.sh)"
```

- **Refuses an Intel Mac** (`sysctl hw.optional.arm64`, which also sees through Rosetta),
  before anything downloads.
- **Downloads the latest release's archive** (or `DINO_VERSION=<v>`), and checks it
  against its `.sha256`. A mismatch stops the install and removes the download.
- **Installs into `~/Applications`** (created if missing). No `sudo`. An existing
  `DinoTraining.app` is replaced only once the new one is unpacked completely.
- **Tests and offline installs:** `DINO_ARCHIVE=<file>` installs a local archive
  (checked against `<file>.sha256`), and `DINO_INSTALL_DIR` changes the target folder.
- **Updates:** run it again.

## The Homebrew formula

- **The file** `packaging/homebrew/dinotraining.rb.template` is filled in per release.
  It belongs in a tap `JanderHungrige/homebrew-tap`:
  `brew install janderhungrige/tap/dinotraining`.
- **It installs the app into the formula's prefix, and a `dinotraining` command** that
  starts it. `depends_on arch: :arm64`.
- **Creating the public tap repository is publishing:** Jan creates it and copies the
  formula in. This wave prepares everything up to that.
- **Updates:** `brew upgrade`.

## "Add to Applications" (in the app)

- A formula may not write outside its prefix. The app itself does it, once, and only
  when asked.
- **When:** the app runs from a Homebrew Cellar (`…/Cellar/dinotraining/<v>/`), and
  `~/Applications/DinoTraining.app` does not exist yet.
- **What:** a slim bar under the header: "Add DinoTraining to your Applications folder?"
  with **Add** and **Not now**. "Not now" is remembered.
- **How:** a symbolic link from `~/Applications/DinoTraining.app` to Homebrew's
  version-independent path (`<prefix>/opt/dinotraining/DinoTraining.app`), so it
  survives `brew upgrade`. Finder, the Dock and `open -a` follow it.

## The README

- **Mac:** the script line, the brew line, and why not to download the archive in the
  browser.
- **For anyone who did:** the one-time "Open anyway" in System Settings → Privacy &
  Security.

## Verified (2026-10-01)

- **The release asset, built as CI builds it:** `DinoTraining_0.0.1_aarch64.app.tar.gz`
  **24 MB** (Wave 8's dmg with the PyInstaller sidecar: 298 MB), its `.sha256`, and the
  rendered `dinotraining.rb` with that version and checksum.
- **The script** (`test_install_mac.sh`, 10 checks, local archives, no network):
  - installs into a folder it creates;
  - the installed app runs and carries no quarantine mark;
  - installing again replaces it;
  - a checksum mismatch refuses, says why, and leaves the installed app alone;
  - an archive without the app refuses.
- **Live:** the real archive installed with the script into a test Applications folder;
  no `com.apple.quarantine`, ad-hoc linker-signed. Started directly: healthy in 5 s.
  **Started through LaunchServices (`open`), the way Finder starts it: no Gatekeeper
  intervention, healthy in 4 s.**
- **The formula:** `render_formula.py` (8 tests: url and checksum filled in, a `v` tag
  accepted, a formula and not a cask, arm64 only, bad versions and checksums refused,
  an unknown placeholder refused). `brew style`: no offenses. The install itself is
  blocked on this Mac by outdated Command Line Tools (see known issues); the local test
  tap was removed again.
- **"Add to Applications":**
  - Rust (5 tests): a Cellar path points at the `opt` path; a custom prefix works; a
    start through the `opt` link is resolved to the Cellar; anything else offers
    nothing.
  - **Found live:** the `dinotraining` command starts the app through Homebrew's `opt`
    link, whose path shows no Cellar, so the first version offered nothing. The shell
    now resolves links first. Live, from the formula's exact layout: "Offering to link
    ~/Applications/DinoTraining.app to …/opt/dinotraining/DinoTraining.app" after 2 s.
  - Frontend (4 tests): asks when offered and adds on request; says nothing when there
    is nothing to offer; "Not now" is remembered and the shell is not asked again;
    outside the shell it does nothing.
- **The README** has the script line, the brew line (once the tap exists), why not the
  browser, "Open Anyway" for anyone who did, and the first-start install explained.

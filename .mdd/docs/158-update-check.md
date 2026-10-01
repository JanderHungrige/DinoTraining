---
id: 158-update-check
title: Update Check — The Installer Edition Says When a New Version Is Out
edition: DinoTraining
depends_on: [156-store-aware-app, 133-download-site]
relates: [130-homebrew-install, 154-store-listing]
source_files:
  - apps/desktop/src-tauri/src/update_check.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/Cargo.toml
  - apps/frontend/src/components/UpdateNotice.tsx
  - apps/frontend/src/App.tsx
  - apps/frontend/src/look.css
  - apps/frontend/src/i18n/en/app.ts
  - apps/frontend/src/i18n/de/app.ts
  - website/privacy.html
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/update_check.rs
  - apps/frontend/src/components/UpdateNotice.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [update-check, release, installer, desktop-shell, privacy]
path: Installer/UpdateCheck
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 158 — Update Check

## Jan (2026-10-01)

- "For the non Microsoft Store versions, we need an update checker. With the start of
  the app, check on updates and inform the user."

## The check (`update_check.rs`, `check_for_update`)

- **Once at start, from the shell,** for the **installer edition only** (doc 156): the
  Store updates its own edition; a dev build is whatever is checked out.
- **Asks the download site's `latest.json`** (doc 133, which the site's updater writes
  from GitHub's latest release), and **GitHub's releases API if the site does not answer.**
  An 8 s timeout each.
- **Compares `x.y.z` as numbers** (0.1.10 > 0.1.9); a leading `v` and a pre-release
  suffix are ignored; an unreadable version means no update.
- **Never in the way:** offline, a timeout, an error status or a malformed answer is a
  warning in the app log and no notice.
- **`DINO_UPDATE_CHECK=0`** (or `false`, `off`, `no`) turns it off.
- **HTTPS:** the shell's `reqwest` had no TLS (it only spoke to the local backend). It now
  uses rustls with the **operating system's root certificates**, so a company proxy with
  its own CA works as it does in the browser.

## The notice (`UpdateNotice`)

- **A slim bar under the header** (the "Add to Applications" bar's style): "DinoTraining
  0.1.3 is available. You have 0.1.2." with:
  - **Get it** → the download site, which gives each platform its own way (the EXE, the
    Mac's install command, the .deb);
  - **What's new** → the release notes;
  - **Later** → remembered **for that version**: the bar returns only when a newer one
    is out.
- **In German** too ("DinoTraining 0.1.3 ist da. Du hast 0.1.2.").

## Privacy

- **The privacy page (doc 154) names it:** once per start, `dino.w3rth.de/latest.json` or
  GitHub; only the app's version goes along (the request's user agent); how to turn it
  off.

## Tests

- **Rust:** versions compare as numbers, prefixes and suffixes; only a newer release is an
  update (equal, older and garbage are not); both answer shapes are read, the site's
  `"version": null` is none; the off switch.
- **Frontend:** the bar's text and both links; "Later" remembered for that version and
  shown again for a newer one (in German); nothing when there is no update, the check
  fails, or there is no shell.
- **Live, once (not in the suite, which never touches the network):** both sources
  answered `0.1.2` over HTTPS through the new TLS stack.

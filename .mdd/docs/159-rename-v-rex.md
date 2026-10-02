---
id: 159-rename-v-rex
title: Rename to V-Rex — The Visible Name Changes, the Machine Keys Stay; the Store Identity Goes In
edition: DinoTraining
depends_on: [151-msix-package, 155-store-submission, 133-download-site, 142-annotation-export]
relates: [130-mac-distribution, 131-installer-smoke-ci, 154-store-listing, 156-store-aware-app, 158-update-check]
source_files:
  - apps/desktop/src-tauri/tauri.conf.json
  - packaging/msix/identity.json
  - packaging/msix/AppxManifest.template.xml
  - backend/app/datasets/exchange/layout.py
routes: []
models: []
test_files: []
data_flow: mixed
last_synced: 2026-10-02
status: in_progress
phase: all
mdd_version: 11
tags: [rename, branding, v-rex, microsoft-store, installer, website]
path: Meta/Rename
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 159 — Rename to V-Rex

## Jan (2026-10-02)

- "I decided to rename the application to V-Rex. Wordplay on T-Rex the dinosaur and
  having our start in mind with dino. But this makes it more open for future development.
  V-Rex stands for Vision-Rex or **Vision Representation & Experimentation**. An AI model
  training pipeline for vision foundation models."
- "We can still keep the DinoTraining for the GitHub for now."
- **Decisions (asked):**
  - **visible name only:** internal ids stay;
  - **no migration** of installed copies (only test installs exist);
  - **the domain stays** `dino.w3rth.de`;
  - **merge first:** 15.10, 157 and 158 went into `dev` (`0a683f0`), the rename branches
    from it.
- **The Store identity**, reserved by Jan:
  - Name `JeanQuestEnterprise.V-Rex`;
  - Publisher `CN=522F9C35-C376-4C5B-9538-6CD2068FA92D`;
  - PublisherDisplayName `JeanQuestEnterprise`;
  - PFN `JeanQuestEnterprise.V-Rex_f2f23w3rhp35p`;
  - Store ID `9PKPPDW39FCZ`.

## The rule

- **What a person reads becomes "V-Rex".**
- **What a machine keys on stays,** so nothing installed, stored or exported so far is
  stranded.

## Checklist: renamed

- [ ] **Desktop shell:**
  - `productName` and the window title → `V-Rex`, with the descriptions;
  - the Cargo description;
  - user-facing errors (sidecar, VC runtime);
  - the issue report header and the update check's user agent.
  - Consequences:
    - the installers become `V-Rex_<v>_x64-setup.exe`, `V-Rex.app`, `v-rex_<v>_amd64.deb`;
    - Windows installs to `%LOCALAPPDATA%\V-Rex` and lists "V-Rex" under Apps.
- [ ] **Mac:**
  - `mac_apps.rs` (`V-Rex.app`, the formula `v-rex`);
  - `install-mac.sh`;
  - the Homebrew template (`v-rex.rb`, class `VRex`, command `v-rex`);
  - `render_formula.py` and their tests.
- [ ] **Windows installer:** the NSIS uninstall message.
- [ ] **Release workflow:**
  - Mac archive name and `.app`;
  - the formula file;
  - Windows smoke: the app at `%LOCALAPPDATA%\V-Rex`, its runtime and data still in
    `%LOCALAPPDATA%\DinoTraining`, the uninstall key `…\Uninstall\V-Rex`;
  - MSIX file names, certificate, the Store step's wording.
- [ ] **MSIX:**
  - `identity.json` with Jan's identity (`placeholder: false`);
  - `DisplayName` V-Rex;
  - `Executable` `V-Rex.exe`;
  - Application Id `VRex` (an Id allows no hyphen);
  - `stage_msix.py`;
  - `smoke_msix.ps1` (`!VRex`, the package name);
  - the test certificate's subject is the real Publisher.
- [ ] **Frontend:**
  - `<title>`, the header;
  - every UI text in English and German naming the app;
  - the MLflow panel's default experiment;
  - comments that name the product.
- [ ] **Backend:**
  - the API title;
  - the start log;
  - MCP server name `v-rex` and its instructions;
  - the agent guide (title, `claude mcp add … v-rex`, file `v-rex-api-guide.md`);
  - COCO `info.generator`;
  - model export texts and the runtime header;
  - user agents;
  - restore messages and their German;
  - the MLflow default experiment `V-Rex`.
- [ ] **The export folder:**
  - `<target>/v-rex/v-rex.json`, format `v-rex-export`;
  - **read both:** `find_export`, restore and cloud linking accept the old
    `dinotraining/` name and format, so Jan's test exports still restore;
  - writes and save-back use the new name.
- [ ] **Website:**
  - title, texts, download labels, privacy page (EN/DE), emblem title;
  - the Store link once live.
- [ ] **Store listing** (`packaging/store/`):
  - name V-Rex, the expansion and tagline in EN/DE;
  - certification notes.
- [ ] **Docs:**
  - `README.md`, `backend/README.md`, `project-docs/ARCHITECTURE.md`, `CLAUDE.md`'s
    "What this is";
  - `.mdd/HANDOFF.md` and `.startup.md` headers.

## Checklist: kept, on purpose

- **Machine keys:**
  - the data folder `DinoTraining` (`%LOCALAPPDATA%`, `Application Support`,
    `.local/share`) and the Store edition's `…\LocalCache\Local\DinoTraining`;
  - the bundle identifier `com.dinotraining.app`, so the log folder and the webview's
    stored settings carry over;
  - `DINO_*` settings and the browser storage prefix `dinotraining.v1.*`;
  - `dinotraining.db`.
- **Formats, events and tags:**
  - the export kind id `dinotraining` (an API value, never shown);
  - the model card schema `dinotraining.model-card/1`;
  - MLflow tag keys `dinotraining.*` (the backfill keys on them);
  - the export-settings event name.
- **Code names:** the Cargo crate `dinotraining`/`dinotraining_lib` and the Python package
  `app`.
- **The repository** `github.com/JanderHungrige/DinoTraining`, every URL to it, and the
  domain `dino.w3rth.de` (and the server's `~/dinotraining-site`).
- **The ".mdd" history:** past docs describe what was built under the old name.
- **"Dino Run",** the setup screen's game: the T-Rex is the point of the new name.

## Verification

- All suites (frontend, Rust, backend, script tests); a grep that leaves only the kept
  list.
- A release dry run: the three installers under their new names, both Windows smoke tests
  with the split folders, the MSIX under the real identity.
- The running app: the window, header, setup screen and an export folder.

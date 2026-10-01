---
id: dinotraining-wave-15-10
title: "Wave 15.10: The Microsoft Store — an MSIX edition beside the EXE, signed by Microsoft"
initiative: dinotraining
initiative_version: 16
status: in_progress
depends_on: dinotraining-wave-15-9
demo_state: "DinoTraining is in the Microsoft Store. Installing it there shows no 'Windows protected your PC' warning (Microsoft signs the MSIX), its first start sets up Python and PyTorch exactly as the EXE does (the Visual C++ runtime included), the Store updates it, and uninstalling it after the in-app notice keeps every exported dataset and model. Each release builds the EXE as before and an MSIX, installs and starts the MSIX in CI, and attaches it to the GitHub release for the Store; the download site links to the Store beside the EXE."
created: 2026-10-01
hash: ea9777cf
---

# Wave 15.10: The Microsoft Store

**Jan (2026-10-01):**
- "I would like to keep the exe build also. But let's plan the Microsoft App Store route."
- "First cloud, then MS Store." Wave 15.9 is built and in `dev`.
- "Partner Center account: is that only for businesses? Can I add also my private
  person?" Answered below; his choice is decision **D0**.

## What the Store gives, and what it does not (checked 2026-10-01)

- **It gives:**
  - an account for an individual (a private person), free (ID and selfie), or for a
    company (D0);
  - **MSIX packages re-signed by Microsoft after certification:** no certificate to buy,
    no SmartScreen warning for Store installs;
  - hosting, distribution and automatic updates.
- **It does not:**
  - sign EXE or MSI listings: the free signature is MSIX only;
  - sign the download site's EXE, which stays unsigned. The Store is a second channel,
    not a replacement.
- **Policy:**
  - 10.2.2 allows code loaded after install when it serves the described function
    (PyTorch does);
  - 10.2.4 asks for such dependencies to be named at the start of the description.

## D0 — individual or company account (Jan decides before feature 5)

| | Individual | Company |
|---|---|---|
| Cost | free (ID + selfie) | free since 2025 |
| Publisher shown | his own name | the registered company's name, with email, address, phone on the product page |
| For | distribution "not in relation to business, trade or profession": hobby, personal, non-commercial | distribution in relation to a business or profession |
| Team members | none: one person manages it | several users with roles |
| Store submission API (feature 5's automation) | **uncertain:** the API authenticates an Entra ID application; individual accounts sign in with a personal Microsoft account only. To be checked (research R4) | supported |
| Change later | **not possible:** individual → company means a new account and a new listing | — |

- **The question for Jan:**
  - Is DinoTraining distributed in relation to his profession or a company (Quest
    Enterprise, his employer)? Then the account should be a company account from the
    start.
  - If it is a personal, non-commercial project, an individual account fits. The plan
    works with either: without the API, feature 5 stays one manual upload per release.

## What MSIX changes for this app (from Wave 15.9's planning)

- **The install folder is read-only** (`WindowsApps`). The bundled backend and uv are
  only read; the runtime and the data go to `%LOCALAPPDATA%\DinoTraining`, as now.
- **New folders under `AppData` are redirected** to a per-package location and **deleted
  on uninstall.**
  - Accepted (Jan): user work is exported (Wave 15.9, docs 142–145) and the app says so
    (doc 146), which under MSIX is the only warning.
- **Child processes** (uv, python) run in the package's context and see the same folders.
- **Updates come from the Store.** A new lock is synced at the next start (doc 129),
  unchanged.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | msix-package | docs/151-msix-package.md | complete | — |
| 2 | msix-runtime | docs/152-msix-runtime.md | in_progress (Jan's PCs, R1–R3) | msix-package |
| 3 | msix-smoke-ci | docs/153-msix-smoke-ci.md | complete | msix-package, msix-runtime |
| 4 | store-listing | docs/154-store-listing.md | in_progress (screenshots) | — |
| 5 | store-submission | docs/155-store-submission.md | in_progress (Jan's steps) | msix-smoke-ci, store-listing, D0 |
| 6 | store-aware-app | docs/156-store-aware-app.md | in_progress (under package identity on Jan's PCs) | msix-runtime |

### Feature notes

1. **msix-package (151): an MSIX from the same build.**
   - **The release workflow's Windows job** builds the app as now (NSIS stays exactly as
     it is), then stages:
     - `DinoTraining.exe`;
     - **the `runtime/` resources** (backend source, uv). Microsoft's Tauri guide stages
       only the exe; this app cannot start without them;
     - `Package.appxmanifest` and the Store logos (`Square44x44Logo.png`,
       `Square150x150Logo.png`, `StoreLogo.png`…, already made by `tauri icon` from the
       emblem, doc 134).
   - **It packs them with Microsoft's `winapp pack`** (`winget install
     microsoft.winappcli` on the runner).
   - **`Package.appxmanifest`:**
     - `Identity Name` and `Publisher` from Partner Center (after Jan reserves the name;
       until then, placeholders for CI);
     - `DisplayName` "DinoTraining", `PublisherDisplayName` per D0;
     - one `Application` with `EntryPoint="Windows.FullTrustApplication"`;
     - the capabilities `runFullTrust` and `internetClient`;
     - `TargetDeviceFamily Windows.Desktop`, MinVersion 10.0.17763.0 (Windows 10 1809,
       WebView2's floor);
     - x64.
   - **Version:** the app's `0.1.3` becomes `0.1.3.0`. The fourth part must be 0 for the
     Store, and every upload must be higher than the last.
   - **Output, beside the EXE in the GitHub release:**
     - `DinoTraining_<v>_x64.msix` unsigned, for the Store;
     - the same signed with a self-signed test certificate (`winapp cert generate`) for
       the smoke test and for testers who trust that certificate. It is not published as
       an end-user download.
2. **msix-runtime (152): the app works under package identity.**
   - **Measured on a Windows runner and then on Jan's PCs**, installed from the MSIX:
     - the first-run setup (doc 127), including the Visual C++ runtime (doc 141);
     - the CPU⇄GPU switch (doc 128);
     - an update with a new lock (doc 129);
     - the backend log and "Open the log" (docs 139/140);
     - exports and "Open the data folder" (docs 59, 142–144);
     - the cloud cache (doc 149).
   - **Paths:** what `%LOCALAPPDATA%\DinoTraining` really is under redirection, and what
     the app shows the user (the redirected path, so "Open the folder" opens the right
     one).
   - **The Visual C++ runtime (doc 141) under MSIX:**
     - option (a): the manifest declares the framework package
       `Microsoft.VCLibs.140.00.UWPDesktop`, which the Store installs with the app;
       whether it serves `python.exe`, which lives outside the package, is research R2;
     - option (b): doc 141's installer as now (one admin prompt); whether certification
       accepts it under 10.2.3 is research R3;
     - decided by measurement, not assumption.
   - **WebView2:** present on Windows 11 and most Windows 10 machines; an MSIX cannot run
     Tauri's bootstrapper. Research R1 decides between "Windows 11 / WebView2 required"
     and a check at start with a link.
3. **msix-smoke-ci (153): installed and started in CI, like a user would.**
   - **On `windows-latest`:**
     - trust the test certificate;
     - `Add-AppxPackage`;
     - start through the package (`explorer.exe shell:AppsFolder\<AUMID>`), so it has
       package identity and **no inherited standard handles** (the gap doc 139 found);
     - unattended setup (`DINO_SETUP_AUTO=cpu`, passed through a file in the package's
       data folder, since a packaged start inherits no environment);
     - `/health`;
     - a second start without setup;
     - `Remove-AppxPackage`;
     - check that the redirected data folder is gone.
   - **Runs in the release workflow** (and its dry run) beside doc 131's EXE smoke test.
4. **store-listing (154): what the Store page says**, as files in the repo
   (`packaging/store/`), so each release can carry them.
   - **Name, short and long description, keywords, in English and German.** The first
     lines name the first start's download (Python and PyTorch from pytorch.org, PyPI and
     GitHub, about 1–6 GB) per 10.2.4.
   - **Screenshots** (at least one, 1366×768 or larger) from the running app: Models &
     Datasets, the Studio, Training, Inference.
   - **A privacy policy page:** `https://dino.w3rth.de/privacy` (the Store requires one).
     - It says what the app sends where: downloads from pytorch.org, PyPI, GitHub,
       Hugging Face and Microsoft; the user's own cloud storage (Wave 15.9); MLflow if
       set up; no telemetry.
     - It is served by doc 133's site, in English and German.
   - **Age rating** (IARC questionnaire: no objectionable content), **category**
     (Developer tools), **licence terms** (the repo's licence), **support contact** (the
     GitHub issues page, doc 140).
5. **store-submission (155): from the release.**
   - **Jan's one-time steps** (a checklist in the doc):
     1. the account at storedeveloper.microsoft.com, per D0;
     2. reserve the name "DinoTraining";
     3. copy the identity (`Identity Name`, `Publisher`) into the repo's manifest
        settings;
     4. fill the listing from `packaging/store/`;
     5. upload the first MSIX by hand;
     6. submit for certification.
   - **Each release afterwards:**
     - **automated** where the account allows the submission API (R4): the release
       workflow uploads the MSIX as a new submission (Partner Center credentials as
       GitHub secrets) and commits it for certification;
     - **otherwise one manual upload:** the GitHub release carries the MSIX, the
       workflow's summary gives the steps.
   - **Certification takes hours to days.** The GitHub release and the download site do
     not wait for it.
6. **store-aware-app (156): the app knows where it came from.**
   - **Detected at runtime** through the package identity (Rust: the `windows` crate's
     `Package::Current`), exposed to the UI as `edition: store | installer | dev`.
   - **Under the Store:**
     - the uninstall notice (doc 146) words "uninstall from Windows Settings removes
       everything inside the app" (no ticked box there);
     - no "a new version is available, download it" hint (the Store updates);
     - "Open the data folder" opens the redirected folder.
   - **The download site** (doc 133): a "Get it from Microsoft" badge beside the EXE,
     once the listing is live.

## Decisions taken in planning (Jan to confirm)

- **D0: individual or company account** (above). Open.
- **D1: two Windows channels:**
  - the Store (MSIX, signed by Microsoft, updated by the Store);
  - the site (EXE, unsigned, as now).
  - Same build, same version.
- **D2:** x64 only, as the EXE. Arm64 Windows if asked for.
- **D3:** the Store edition shows no update hint of its own.
- **D4:** the minimum is Windows 10 1809 unless R1 shows WebView2 must be guaranteed;
  then Windows 11.

## Built (2026-10-01/02, with placeholders)

- **The MSIX** is packed beside the EXE from the same Windows build (makeappx, not winapp),
  test-signed for CI, and **installed, set up, started twice and removed in CI from a clean
  AppData** (run 36933854791).
- **R5 answered, and it changed the design:** through the AppData redirection uv's Python
  link fails, and an existing folder switches the redirection off. The Store edition now
  writes to its package folder by its real path (doc 152).
- **R4 answered:** the submission API needs an Entra application on Partner Center's Users
  page, which an individual account does not have: one manual upload per release (doc 155).
- **Placeholders:** the identity `DinoTraining.Placeholder` / `CN=DinoTraining Placeholder`
  in `packaging/msix/identity.json` until Jan reserves the name.

## Open research (answered while building, in this order)

- **R1:** WebView2 under MSIX on Windows 10. Present, installable from the app, or a
  requirement?
- **R2:** does the `Microsoft.VCLibs.140.00.UWPDesktop` framework dependency reach a
  `python.exe` outside the package? If not, doc 141's installer stays.
- **R3:** does certification accept an app that installs Microsoft's redistributable
  itself (policy 10.2.3, "secondary software")?
- **R4:** the Store submission API for an individual account (the Entra ID application it
  needs).
- **R5:** redirected `AppData` with uv's hard links and its cache: any path or link the
  redirection breaks?

## Jan's part, in order

1. **D0:** individual or company.
2. Open the account and **reserve "DinoTraining"**; send the identity (`Identity Name`,
   `Publisher`). Until then the work runs with placeholders.
3. Test the MSIX on both Windows PCs (with the test certificate) before the first
   submission.
4. The first upload and submission (feature 5's checklist).

*(This wave is not complete until the demo state can be shown in the running app.)*

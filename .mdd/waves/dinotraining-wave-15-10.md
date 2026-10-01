---
id: dinotraining-wave-15-10
title: "Wave 15.10: The Microsoft Store — an MSIX edition beside the EXE, signed by Microsoft"
initiative: dinotraining
initiative_version: 16
status: planned
depends_on: dinotraining-wave-15-9
demo_state: "DinoTraining is in the Microsoft Store. Installing it there shows no 'Windows protected your PC' warning (Microsoft signs the MSIX), its first start sets up Python and PyTorch exactly as the EXE does, the Store updates it, and uninstalling it after the in-app notice keeps every exported dataset and model. Each release builds the EXE as before and an MSIX, smoke-tests the MSIX on Windows, and submits it to the Store; the download site links to the Store beside the EXE."
created: 2026-10-01
hash: 56da2857
---

# Wave 15.10: The Microsoft Store

**Jan (2026-10-01):** the Store signs MSIX packages for free.
- "I would like to keep the exe build also. But let's plan the Microsoft App Store
  route."
- After Wave 15.9: "First cloud, then MS Store."

## What the Store gives, and what it does not (checked 2026-10-01)

- **It gives:**
  - an individual developer account for free (ID and selfie verification);
  - **MSIX packages re-signed by Microsoft after certification:** no certificate to
    buy, no SmartScreen warning for Store installs;
  - hosting, distribution and automatic updates.
- **It does not sign EXE or MSI listings.** Those need an own certificate, so the
  free signature is MSIX only.
- **The download site's EXE stays unsigned.** The Store is a second channel, not a
  replacement.
- **Policy:**
  - 10.2.2 allows code loaded after install when it serves the described function
    (PyTorch does);
  - 10.2.4 asks for such dependencies to be named at the start of the description.

## What MSIX changes for this app

- **The install folder is read-only** (`WindowsApps`). The bundled backend and uv are
  only read; the runtime goes to `%LOCALAPPDATA%`, as now (doc 126).
- **New folders under `AppData` are redirected** to a private per-package location and
  **deleted on uninstall.**
  - Python, PyTorch, models, the database: removed with the app, which is right for
    everything but the user's work.
  - Wave 15.9 makes that work exportable and says so in the app.
  - There is **no uninstaller page** under MSIX, so the in-app notice (doc 146) is the
    only warning.
- **Child processes** (uv, python) run in the app's package context and see the same
  redirected folders.
- **Updates come from the Store.** An update with a new lock is synced at start (doc
  129), unchanged.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | msix-package | docs/151-msix-package.md | planned | — |
| 2 | msix-runtime | docs/152-msix-runtime.md | planned | msix-package |
| 3 | msix-smoke-ci | docs/153-msix-smoke-ci.md | planned | msix-package, msix-runtime |
| 4 | store-listing | docs/154-store-listing.md | planned | — |
| 5 | store-submission | docs/155-store-submission.md | planned | msix-smoke-ci, store-listing |
| 6 | store-aware-app | docs/156-store-aware-app.md | planned | msix-runtime |

### Feature notes

1. **msix-package (151): an MSIX from the same build.**
   - **The release workflow's Windows job** builds as now, then stages the app's exe
     **and its `runtime/` resources** (the backend source, uv) and packs them with
     Microsoft's `winapp pack`. Microsoft's Tauri guide stages only the exe; this app
     cannot run without its resources.
   - **`Package.appxmanifest`:**
     - identity and publisher from Partner Center;
     - a full-trust desktop app (`runFullTrust`);
     - x64;
     - the emblem's assets, from `tauri icon`.
   - **Version:** `0.1.3` becomes `0.1.3.0`. The Store needs every upload's version
     higher than the last.
   - **For CI and local tests:** signed with a self-signed test certificate. The Store
     upload is unsigned; Microsoft signs it.
   - **The EXE (NSIS) stays exactly as it is.**
2. **msix-runtime (152): the app works under package identity.**
   - **Verified installed from the MSIX:**
     - the first-run setup;
     - the CPU⇄GPU switch (doc 128);
     - an update with a new lock (doc 129);
     - the backend log (doc 139), "Open the log" (doc 140), the exports (15.9).
   - **The Visual C++ runtime (doc 141) under MSIX:**
     - whether the Store accepts an app that installs Microsoft's redistributable
       (policy 10.2.3 forbids "secondary software" that does not serve the app; this
       one does);
     - or whether the manifest's framework dependency (`Microsoft.VCLibs`) can serve
       `python.exe`, which lives outside the package.
     - Measured, not assumed.
   - **WebView2:** Windows 11 has it. Windows 10 may not, and an MSIX cannot run Tauri's
     bootstrapper the way the NSIS installer does. Measured on a Windows 10 runner.
   - **Paths:** what `%LOCALAPPDATA%\DinoTraining` resolves to under redirection, and
     what "Open the data folder" (doc 59) and the log show the user.
3. **msix-smoke-ci (153): the MSIX installed and started in CI.**
   - Doc 131's smoke test against the MSIX: `Add-AppxPackage` with the test
     certificate, an unattended first start (`DINO_SETUP_AUTO=cpu`), `/health`, a
     second start, `Remove-AppxPackage`.
   - Started like the Start menu does (no inherited standard handles), the gap doc 139
     found in the EXE's smoke test.
4. **store-listing (154): what the Store page says.**
   - **Name, description and screenshots in English and German.** The first lines say
     what the first start downloads (Python, PyTorch, about 1–6 GB) and from where
     (10.2.4).
   - **A privacy policy URL** (the Store requires one): a page on dino.w3rth.de stating
     what the app sends where. That is only the downloads from pytorch.org, PyPI,
     GitHub, Hugging Face and Microsoft, plus the user's own cloud storage (15.9). No
     telemetry.
   - **Age rating questionnaire, category** (Developer tools / Productivity),
     **licence terms.**
5. **store-submission (155): from the release, automatically.**
   - **The first submission is by hand (Jan):**
     - the Partner Center account;
     - reserving the name "DinoTraining";
     - the listing;
     - the first upload.
   - **Afterwards, the release workflow:**
     - uploads each new MSIX as a submission through the Store submission API
       (Partner Center credentials as GitHub secrets);
     - Jan's step stays only where Microsoft requires a person.
   - **Certification takes hours to days.** The GitHub release and the download site do
     not wait for it.
6. **store-aware-app (156): the app knows it came from the Store.**
   - **Detected at runtime** through the package identity (`Package::Current`).
   - **Under the Store:**
     - no "Add to Applications" offer (macOS only anyway);
     - the uninstall notice worded for "uninstall from Windows settings";
     - no hint to download updates from the site.
   - **The download site:** a "Get it from Microsoft" badge beside the EXE, once the
     listing is live.

## Decisions taken in planning (Jan to confirm)

- **D1, two Windows channels:**
  - the Store (MSIX, signed by Microsoft, updated by the Store);
  - the site (EXE, unsigned, as now).
  - Both from the same build, the same version.
- **D2:** x64 only, as the EXE. Arm64 Windows if asked for.
- **D3:** the Store edition has no own update hint; the Store updates it.

## Open research

- **WebView2 under MSIX on Windows 10:** present, installable, or a minimum Windows 11?
- **The Visual C++ runtime:** the Store's view of doc 141's installer, versus a
  `Microsoft.VCLibs` framework dependency reaching an out-of-package `python.exe`.
- **Redirected `AppData`** with uv's hard links and cache: any path or link the
  redirection breaks.
- **The submission API's credentials** for an individual (not organisation) account.

*(This wave is not complete until the demo state can be shown in the running app.)*

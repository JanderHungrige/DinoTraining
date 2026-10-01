---
id: 155-store-submission
title: Store Submission — Jan's One-Time Steps, and One Upload per Release
edition: DinoTraining
depends_on: [151-msix-package, 153-msix-smoke-ci, 154-store-listing]
relates: [156-store-aware-app, 133-download-site]
source_files:
  - .github/workflows/release.yml
  - packaging/msix/identity.json
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [microsoft-store, partner-center, submission, release, checklist]
path: Installer/Windows/MSIX/Submission
initiative: dinotraining
wave: dinotraining-wave-15-10
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 155 — Store Submission

## Purpose

- **From a GitHub release to the Microsoft Store.** The GitHub release and the download
  site never wait for certification (hours to days).

## R4: the submission API (checked 2026-10-01)

- **The API authenticates an Entra ID application** that is added on Partner Center's
  Account settings → **Users** page with the Manager role, in an Entra directory the
  account is associated with.
- **An individual account has one user and no Users page:** the API is out of reach. A
  company account could use it.
- **So, per D0:**
  - **individual:** one manual upload per release (below);
  - **company:** the same to start; automation (Partner Center credentials as GitHub
    secrets, a submission created and committed by the release workflow) can follow as
    its own doc. Note Microsoft's warning: a submission created by the API must only be
    changed through the API.

## Jan's one-time steps

1. **D0:** an individual or a company account at storedeveloper.microsoft.com (free; ID
   and selfie for an individual). Cannot be changed later.
2. **Reserve the name "DinoTraining"** (Apps and games → New product → MSIX or PWA app).
3. **Send the identity:** Product management → Product identity: `Package/Identity/Name`,
   `Package/Identity/Publisher` and `PublisherDisplayName`. They go into
   `packaging/msix/identity.json` with `"placeholder": false`; the next release's MSIX
   carries them.
4. **Test the test-signed MSIX on both Windows PCs** (the `msix-test` artifact of a
   release run: trust `DinoTraining_test.cer` in "Trusted People", then open the `.msix`).
5. **The first submission in Partner Center** (the API, if ever, needs one made by hand):
   - Pricing and availability: free, all markets (or private for a first trial);
   - Properties, age rating: `packaging/store/README.md`;
   - Packages: the release's `DinoTraining_<version>_x64.msix` (unsigned; Microsoft signs);
   - Store listings: `packaging/store/listing-en.md`, `listing-de.md`, the screenshots;
   - Submission options → notes for certification: from the README;
   - Submit for certification.
6. **When it is live:** send the Store link; the download site (doc 133) gets a "Get it from Microsoft" badge beside the EXE.

## Each release afterwards

- **The release workflow's summary** says what to do with its MSIX: upload it as a new
  submission's package and submit. While the identity is the placeholder, it says the
  MSIX is not for the Store yet.
- **Versions:** each upload must be higher than the last; the app's `x.y.z` becomes
  `x.y.z.0` (doc 151), so every release qualifies.

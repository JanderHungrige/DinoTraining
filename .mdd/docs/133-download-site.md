---
id: 133-download-site
title: Download Site — dino.w3rth.de and dino.questenterprise.de, Updated Automatically from main and Its Releases
edition: DinoTraining
depends_on: [130-mac-distribution, 131-installer-smoke-ci, 132-uninstall]
relates: [58-installers]
source_files:
  - website/index.html
  - website/site.css
  - website/site.js
  - website/deploy/update-site.sh
  - website/deploy/compose.yml
  - website/deploy/nginx.conf
  - website/deploy/README.md
  - .github/workflows/release.yml
routes: []
models: []
test_files:
  - website/deploy/test_update_site.sh
data_flow: greenfield
last_synced: 2026-10-01
status: in_progress
phase: all
mdd_version: 11
tags: [website, download, release, deploy, nginx, cron, server]
path: Distribution/DownloadSite
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: [../3dmap, ../Battlefuel, ../NinaNatur, ../funding-tender-tracker]
---

# 133 — Download Site

## Purpose

- **Jan (2026-10-01):** "the three installers (or the Mac terminal instructions) and a
  link to the repo on a web page to download", at
  - `dino.w3rth.de`, Nginx Proxy Manager → `172.17.0.1:8002`;
  - `dino.questenterprise.de`, NPM → `172.17.0.1:8003`.
- **The app's video as a moving background.**
- **"As soon as a merge into main brings a new version, update automatically."**
- **The server also runs Tender, 3dmap, Battlefuel, NinaNatur, pdf2audiobook and
  ctt-report.** Nothing of theirs is touched.
- This is not Wave 16's website (accounts, compute). That is still to be rethought.

## What the page shows

- **Windows:** a button for the `.exe`, and the one-time SmartScreen note.
- **macOS:** the terminal line of doc 130 with a copy button, and why not the browser.
- **Linux:** a button for the `.deb`, and the `apt` line.
- **The version and its date,** a link to all releases, and the repository.
- **What the first start does:** about 1 GB from the official sources; NVIDIA via CUDA,
  Apple GPU via MPS.
- **English and German:** the browser's language decides, and a switch overrides it.
- **The particle loop** from the app (Pixabay #5192, credited in the footer) as the
  background.
  - With `prefers-reduced-motion`, its still poster instead.
  - Text on raised surfaces, as in the app (doc 80's contrast).
- **Before the first published release,** the buttons say "first release coming" and
  point to the repository. They never show a broken link.

## How it stays current

```
merge → main ──► release.yml: build + smoke-test all three installers
                 └─ new version (tauri.conf.json) and no release for it yet
                    → publish release v<version> with the assets (no longer a draft)
server, jan's crontab, every 10 min: website/deploy/update-site.sh
  ├─ main's commit (git ls-remote) changed → fetch website/ + the video at that commit,
  │    render into sites/<sha>/, switch the `current` link (one rename)
  └─ GitHub's latest release changed → write latest.json (version, date, asset links)
nginx:alpine "dinotraining-site" serves current/ on 172.17.0.1:8002 and :8003
```

- **A release on every version bump, published, not a draft.** Wave 8 kept drafts so
  that a human published. Jan now wants a merge to main to be the release.
  - **Gate:** all three installers built and smoke-tested (doc 131).
  - A merge without a version bump builds and tests, but publishes nothing.
- **The page reads `latest.json`, written on the server,** not GitHub's API: no
  per-visitor rate limit, and the page works when GitHub is slow.
- **Until main carries `website/`,** the updater takes it from `dev`. It says so in
  its log.
- **Nothing in /opt, nothing as root:** everything lives in `/home/jan/dinotraining-site`,
  in `jan`'s crontab, and in a container of its own. The other projects deploy through
  root's crontab and are left alone.

## Not in our hands

- **DNS:** `dino.questenterprise.de` resolves to `46.38.243.234` (questenterprise.de's
  web host), not to this server, whose NPM already knows the name. Jan points the
  record at `159.195.148.193`.
- **NPM's certificates** for both names: Jan, in NPM, once DNS points here.

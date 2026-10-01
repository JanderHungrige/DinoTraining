---
id: 140-error-report
title: Beside Every Startup Error — Open the Log, Report an Issue (a Prefilled GitHub Issue)
edition: DinoTraining
depends_on: [139-backend-streams, 127-first-run-setup]
relates: []
source_files:
  - apps/desktop/src-tauri/src/error_report.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/frontend/src/components/ErrorActions.tsx
  - apps/frontend/src/setup/SetupFailureNotice.tsx
  - apps/frontend/src/components/BackendStatus.tsx
  - apps/frontend/src/i18n/en/app.ts
  - apps/frontend/src/i18n/de/app.ts
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/desktop/src-tauri/src/error_report.rs (unit tests)
  - apps/frontend/src/components/ErrorActions.test.tsx
data_flow: reads-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [errors, logging, github, issues, support, privacy]
path: Support/ErrorReport
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The buttons were not clicked in the packaged window (no click permission in this session); the commands are unit-tested, and the generated URL was checked by decoding it."
security_read_sites: []
sister_projects: []
---

# 140 — Open the Log, Report an Issue

## Purpose

- **Jan (2026-10-01):** "When an error pops up, add a button that opens the log
  (WordPad, or whatever is installed) and a button 'report issue' that reports the issue
  and the log as a bug on GitHub."

## The two buttons

- **Where:** beside the setup screen's failure, and beside the header's "backend not
  reachable". Desktop app only: outside it there is no log to open.
- **Open the log:**
  - opens `backend.log` (doc 139) with the system's default program for it: Notepad or
    WordPad on Windows, Console or TextEdit on macOS (`tauri-plugin-opener`'s
    `open_path`);
  - no log yet: says where it would be.
- **Report an issue:** opens `github.com/JanderHungrige/DinoTraining/issues/new` in the
  browser, prefilled:
  - **title** `[<os> <version>] <first line of the error>`;
  - **body:** what happened (for the user to fill in), the error, the version, OS and
    architecture, and the backend log's last 40 lines;
  - **label** `bug`.
  - **The user reads it and submits it with their own GitHub account.** Posting from the
    app would need a token inside a publicly distributed binary, which is a secret
    given away.
  - **The home folder is replaced by `~`** in the error and the log, so a user name
    does not reach a public issue unnoticed.
  - **GitHub's URL limit:** the URL stays under 7 500 characters. The log loses its
    oldest lines first, because the end holds the traceback.

## Verified (2026-10-01)

- **Rust (4 tests):**
  - the issue carries the error, the version and the log, labelled `bug`;
  - a Windows home folder never reaches it;
  - a 2 000-line log is cut from its start to fit, keeping the final `ValueError`;
  - no log says so.
- **The URL from a real-shaped traceback,** decoded: title `[windows 0.1.1] backend
  exited during startup (exit code: 1).`, the path shown as `~/AppData/Local/…`,
  674 characters.
- **Frontend (5 tests):**
  - opens the log;
  - says why when there is none;
  - reports with the very error shown;
  - absent outside the desktop app;
  - German.
  - The whole suite: 1133 passed.

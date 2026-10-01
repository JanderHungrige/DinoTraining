---
id: 139-backend-streams
title: The Backend without Standard Streams — the Windows Start Failure of 0.1.0, and a Log Users Can Find
edition: DinoTraining
depends_on: [126-bundled-python, 127-first-run-setup, 131-installer-smoke-ci]
relates: [132-uninstall]
source_files:
  - backend/app/core/streams.py
  - backend/app/__main__.py
  - apps/desktop/src-tauri/src/backend_log.rs
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/desktop/src-tauri/src/lib.rs
routes: []
models: []
test_files:
  - backend/tests/test_streams.py
  - apps/desktop/src-tauri/src/backend_log.rs (unit tests)
data_flow: writes-existing
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [installer, windows, startup, logging, uvicorn, bugfix]
path: Installer/BackendStreams
initiative: dinotraining
wave: dinotraining-wave-15-7
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The Windows smoke test (doc 131) starts the app with its output redirected, so it never saw this. A test that launches it like Explorer does (no standard handles, no inherited environment) is still to be found; meanwhile the release build never inherits streams, and the backend test covers None streams on every OS."
security_read_sites: []
sister_projects: []
---

# 139 — The Backend without Standard Streams

## What happened (Jan, Windows, release 0.1.0)

- **The CPU setup ran through.** At its very end: "the installation was aborted. The
  backend exited during startup (exit code: 1) — see the log above for the Python
  traceback." **There was no log.**

## Why

- **No standard handles on Windows:** a GUI app started from the Start menu has none,
  and the shell let the backend **inherit** its standard streams. Python then starts
  with `sys.stdout = None` and `sys.stderr = None`.
- **uvicorn's logging setup** calls `sys.stdout.isatty()` and fails: "Unable to
  configure formatter 'default'", exit code 1.
- **The traceback had nowhere to go.**
- **Reproduced here:**
  - `python -m app` with its stdout and stderr closed: exit code 1;
  - the traceback, captured in-process: the formatter error above.
- **Why CI was green:** doc 131's smoke test starts the app with its output redirected
  to a file, so the app had handles to pass on.
- **Why macOS hides it:** a process started with fds 1 and 2 closed reuses them for its
  first open files, so the backend still inherits *something*.

## The fix, two layers

1. **The backend survives missing streams** (`app/core/streams.py`). `python -m app`
   gives a missing stdout or stderr an `os.devnull` writer before anything else is
   imported. Whoever starts the backend, it no longer dies of this.
2. **The packaged app never inherits** (`backend_log.rs`).
   - The backend writes to `backend.log` in the app's log folder:
     - Windows `%LOCALAPPDATA%\com.dinotraining.app\logs`;
     - macOS `~/Library/Logs/com.dinotraining.app`.
   - The previous run's output stays as `backend.previous.log`.
   - **A start that fails, or never answers, quotes the log's last 15 lines in its
     error**, which the setup screen and the app show, with the file's path.
   - A development run (debug build) keeps the terminal.
   - `PYTHONIOENCODING=utf-8`, so the log is UTF-8 on every OS.

## Verified (2026-10-01)

- **Backend (3 tests):**
  - missing streams are replaced and present ones kept;
  - nothing changes with real streams;
  - `python -m app` serves `/health` with fds 1 and 2 closed. **This test fails on the
    old entry point** ("the backend exited with 1") and passes now.
- **Rust (5 tests):**
  - a new run keeps the previous log;
  - the tail skips blank lines;
  - a huge log is read from its end only;
  - the error quotes the traceback, or says the log was empty, or points at the
    terminal;
  - a missing log gives nothing.
- **The release app, started without standard streams** (empty runtime, unattended
  setup): healthy after 70 s, and `backend.log` holds uvicorn's output.

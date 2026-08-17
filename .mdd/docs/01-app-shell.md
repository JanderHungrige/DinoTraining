---
id: 01-app-shell
title: App Shell — Tauri Window, Tabbed UI & FastAPI Sidecar
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-1
wave_status: complete
depends_on: []
relates: []
source_files:
  - backend/app/__init__.py
  - backend/app/__main__.py
  - backend/app/main.py
  - backend/README.md
  - backend/app/core/__init__.py
  - backend/app/core/config.py
  - backend/app/core/logging.py
  - backend/app/core/errors.py
  - backend/app/api/__init__.py
  - backend/app/api/v1/__init__.py
  - backend/app/api/v1/router.py
  - backend/app/api/v1/health.py
  - apps/frontend/package.json
  - apps/frontend/tsconfig.json
  - apps/frontend/tsconfig.node.json
  - apps/frontend/vite.config.ts
  - apps/frontend/index.html
  - apps/frontend/src/main.tsx
  - apps/frontend/src/App.tsx
  - apps/frontend/src/test-setup.ts
  - apps/frontend/src/api/types.ts
  - apps/frontend/src/api/client.ts
  - apps/frontend/src/components/TabBar.tsx
  - apps/frontend/src/components/BackendStatus.tsx
  - apps/frontend/src/components/StubPanel.tsx
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/styles.css
  - apps/desktop/src-tauri/Cargo.toml
  - apps/desktop/src-tauri/build.rs
  - apps/desktop/src-tauri/tauri.conf.json
  - apps/desktop/src-tauri/capabilities/default.json
  - apps/desktop/src-tauri/src/main.rs
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/src/sidecar.rs
  - apps/desktop/package.json
  - scripts/dev.sh
  - .claude/launch.json
routes:
  - GET /api/v1/health
models: []
test_files:
  - backend/tests/conftest.py
  - backend/tests/test_health.py
  - backend/tests/test_config.py
  - apps/frontend/src/api/client.test.ts
  - apps/frontend/src/components/TabBar.test.tsx
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [tauri, react, fastapi, sidecar, health-check, api-contract, app-shell]
path: Platform/Shell
integration_contracts:
  - function: apiFetch<T>(path, init)
    when: any frontend call to a /api/v1/* endpoint — never call fetch() directly
    applies_to: all features in this initiative that talk to the backend
  - function: get_settings()
    when: any backend module needing configuration — never read os.environ directly
    applies_to: all backend features in this initiative
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "npm 10.9 crashes resolving vitest 4's optional-peer graph (arborist `edgesOut` null); frontend installs require --legacy-peer-deps. Fix by upgrading npm/Node rather than pinning vitest down."
  - "Node 23.1 is non-LTS; jsdom's whatwg-url wants ^22.14 || >=24 and logs EBADENGINE. Tests pass, but move to Node 24 LTS before Wave 5 packaging."
  - "TypeScript pinned to 5.9.3 while 7.x is npm `latest`. Deliberate for foundation stability; revisit once the vite/vitest toolchain has TS7 mileage."
  - "App icons in apps/desktop/src-tauri/icons/ are generated placeholders. Replace with real artwork before Wave 5 (installers, code-signing)."
  - "Sidecar runs from backend/.venv in dev only; packaged-binary resolution is deliberately deferred to Wave 5 (see sidecar::SidecarConfig::for_development)."
  - "A SIGKILL'd shell still orphans the sidecar — no signal handler can catch SIGKILL. ensure_port_free() reports it on the next launch with the kill command to run. Revisit in Wave 5 if packaging gives a supervisor."
  - "Windows has no signal handler yet (install_signal_handlers is a no-op off unix); wire Ctrl-C handling during Wave 5 packaging."
sister_projects: []
---

# 01 — App Shell — Tauri Window, Tabbed UI & FastAPI Sidecar

## Purpose

Establishes the runnable skeleton every other Wave 1 feature plugs into: a Tauri v2 desktop
window hosting a React + TypeScript tabbed UI, and a FastAPI sidecar process that owns all
ML work. This feature ships no ML behaviour of its own — its deliverable is the *contract*:
a typed `/api/v1` client, a health-check handshake proving the sidecar is alive, and a
`tauri dev` workflow that starts all three layers with one command.

## Architecture

```
┌──────────────── Tauri v2 shell (Rust) — apps/desktop/src-tauri ────────────────┐
│                                                                                │
│  main.rs                                                                       │
│    └─ sidecar.rs  ── spawns ──▶  python -m uvicorn app.main:app                │
│                                  (backend/, port 8756)                         │
│                   ── polls  ──▶  GET /api/v1/health  until ready or timeout     │
│                                                                                │
│  WebView ──▶ React UI (apps/frontend, Vite dev server :1420)                    │
│                └─ api/client.ts ── HTTP ──▶ http://127.0.0.1:8756/api/v1/*      │
└────────────────────────────────────────────────────────────────────────────────┘
```

Three processes in dev (`tauri dev`): Vite dev server, the FastAPI sidecar, and the Tauri
window. In production (Wave 5) the sidecar becomes a bundled binary; nothing above the
`sidecar.rs` boundary changes.

**Layer responsibilities**

| Layer | Owns | Must not |
|-------|------|----------|
| `apps/desktop` (Rust) | Window, sidecar process lifecycle, readiness gate | Contain ML or business logic |
| `apps/frontend` (TS) | Rendering, tab routing, typed API calls | Call `fetch()` directly; know model names |
| `backend` (Python) | All ML, all persistence, all `/api/v1` routes | Know about Tauri |

## Data Model

None. This feature introduces no persistence — SQLite arrives with `03-dataset-store`.

## API Endpoints

### `GET /api/v1/health`

Auth: none (loopback-only service).

Response `200`:
```json
{
  "status": "ok",
  "version": "0.0.1",
  "device": "mps",
  "api_prefix": "/api/v1"
}
```

| Field | Type | Notes |
|-------|------|-------|
| `status` | `"ok"` | Literal — the shell treats any other value as not-ready |
| `version` | `string` | Backend package version |
| `device` | `"cuda" \| "mps" \| "cpu"` | Resolved compute device (`auto` is resolved server-side, never returned) |
| `api_prefix` | `string` | Echoes the configured prefix so the client can assert agreement |

Error cases: none by design — if the process is up this returns 200. A connection error
(process not yet listening) is the "not ready" signal, not a non-200 status.

## Business Rules

- **Device resolution:** `DINO_DEVICE=auto` resolves in priority order CUDA → MPS → CPU.
  An explicit device that is unavailable is a startup error, not a silent downgrade — the
  user asked for it and must be told it is missing.
- **Readiness gate:** the shell polls `/api/v1/health` every 250 ms for up to 60 s. PyTorch
  import alone can take several seconds on a cold start, so a short timeout is a bug.
- **The port is checked before spawning.** If something already listens on 8756 the shell
  fails with that message rather than starting a second backend. Found the hard way: on a
  dev hot-restart the old sidecar survived, the new one died on bind, and the old one
  answered the health probe — so the shell reported "ready" while attached to a process it
  did not own and could not shut down.
- **Readiness polls the child, not just the port.** `wait_until_healthy` takes the `Child`
  and calls `try_wait()` each iteration, so a backend that dies during startup reports
  `BackendExited` instead of timing out 60 s later with no explanation.
- **The child is stored on the handle even when startup fails** — it may still be alive,
  and an unstored child is a leaked process that holds the port after the window closes.
- **Config is read once**, at startup, through `get_settings()` (cached). No module reads
  `os.environ` directly — that is how a setting ends up meaning two different things.
- **All errors are logged with context before being re-raised.** The global exception
  handler returns a shaped JSON error and never leaks a traceback to the client.
- **Never log `HF_TOKEN`.** The settings repr masks it.
- **The frontend never calls `fetch()` directly** — always `apiFetch<T>()`, which owns the
  base URL, JSON handling, and error shaping.

## Data Flow

Greenfield. The one value that flows end-to-end in this feature:

`device` — computed in `backend/app/core/config.py` (`resolve_device()`, torch availability
probe) → transported as `HealthResponse.device` over `GET /api/v1/health` → consumed by
`BackendStatus.tsx`, rendered as a badge in the tab bar. No transformation in between.

## Dependencies

None — this is the wave's root feature. Everything else in Wave 1 depends on it.

## Security

The sidecar binds **loopback only** (`127.0.0.1`), never `0.0.0.0` — it is an in-process
implementation detail of a desktop app, not a network service. No auth is therefore
required in Wave 1, and this is the assumption that must be revisited in Wave 6 (website),
where the same FastAPI core becomes genuinely remote.

`HF_TOKEN` is read from `.env` into settings and is never logged, never echoed by any
endpoint, and masked in `repr()`. `/api/v1/health` deliberately exposes no path or token
information — `device` and `version` only.

CORS is restricted to the Vite dev origin (`http://localhost:1420`) plus the Tauri origin;
it is not `*`.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

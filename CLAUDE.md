# CLAUDE.md — DinoTraining

Project instructions for Claude Code. These extend the global `~/.claude/CLAUDE.md`
(security gatekeeper & standards) and adapt them for this **Python-ML + Tauri/React hybrid**.

## What this is

A sharable, installable desktop app (Tauri + React + FastAPI/PyTorch sidecar) for the
annotate → train → infer → generate-data loop with DINOv2/v3 + Grounding DINO.
Full plan lives in `.mdd/` (initiative `dinotraining`, waves 1–6).

## Stack

- **UI:** React + TypeScript (Vite) — `apps/frontend/`
- **Desktop shell:** Tauri (Rust) — `apps/desktop/`
- **ML backend:** FastAPI + PyTorch — `backend/`
- **Metadata store:** SQLite (single shared connection module — the StrictDB analog here)
- **Datasets/weights:** on disk, never committed

## Language rules (adapted from global)

- **Frontend & Tauri glue → TypeScript, strict mode, no `any`.** `tsconfig.json` strict.
- **Backend/ML → Python** (the global "TypeScript always" rule does not apply to the ML core).
  Use full type hints, `ruff` + `mypy`, Python 3.11+.
- Do not introduce a second language for a layer that already has one.

## API

- All backend endpoints under **`/api/v1/`** (FastAPI). Keep the frontend↔backend contract
  in one typed client module.
- **A validation failure must never surface as a 500.** Handlers that accept external
  input need a `ValueError → 422` backstop below the specific `except` clauses, so a new
  raise site downstream cannot escape as an opaque error with the reason only in the log.
- Watch exception *ordering*: several project errors subclass `LookupError`
  (`ModelNotInstalledError`) or `ValueError` (`IncompatibleHeadError`). Catch the specific
  one first, or a 409 silently becomes a 404.

## React state

- **Never seed `useState` from asynchronously-loaded props.**
  `useState(items[0]?.id ?? '')` runs once, before the fetch resolves, so the state stays
  `''` while a `<select>` renders its first option anyway — the form looks filled in and
  its submit button is disabled forever. Store only the user's *override* and derive the
  effective value:

  ```tsx
  const [override, setOverride] = useState('');
  const selected = override || items[0]?.id || '';
  ```

  Test it by rendering with empty props, then `rerender` with data — that is the sequence
  a real load produces, and the only one that reproduces the bug.

## Quality gates (from global — enforced here)

- No file > 300 lines (split). No function > 50 lines (extract helpers).
- Never swallow errors: log with context before re-throwing. FastAPI needs a global
  exception handler; Python entrypoints handle unhandled exceptions.
- Tests must assert something meaningful ("it runs" is not a criterion). `pytest` for
  backend, `vitest` for frontend.
- TypeScript compiles clean; Python passes `ruff` + `mypy`; no linter warnings.

## Secrets

- **`HF_TOKEN`** (for gated DINOv3) and all cloud creds live in `.env` — NEVER committed.
  `.env` is gitignored; only `.env.example` is tracked.
- Never print tokens in logs or responses.

## ML specifics

- Backbones are **frozen** feature extractors; only heads are trained.
- Preprocessing is derived internally from the chosen backbone + head — do not ask the user.
- Model weights download on demand (admin tab / first run), cached in `DINO_MODEL_CACHE_DIR`;
  never bundled in the installer and never committed.
- Training goes through the **pluggable job runner** interface (local now, hyperscaler later) —
  never hardcode device/training logic into UI or API handlers.

## Workflow

- Build wave-by-wave: `/mdd plan-execute dinotraining-wave-<N>`. One wave per branch.
- Always branch off `dev`; never commit directly to `main`.
- Use Plan Mode for anything bigger than a simple fix.

## Never

- Never commit `.env`, weights, checkpoints, or datasets.
- Never auto-deploy or publish without explicit approval.
- Never do project-wide renames without a checklist.

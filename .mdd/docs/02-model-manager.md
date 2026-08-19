---
id: 02-model-manager
title: Model Manager — Registry, Downloads & Admin Tab
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-1
wave_status: complete
depends_on: [01-app-shell]
relates: []
source_files:
  - backend/app/core/paths.py
  - backend/app/ml/__init__.py
  - backend/app/ml/registry.py
  - backend/app/ml/downloads.py
  - backend/app/api/v1/models.py
  - backend/app/api/v1/system.py
  - apps/frontend/src/api/models.ts
  - apps/frontend/src/hooks/useModels.ts
  - apps/frontend/src/components/ModelCard.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
routes:
  - GET /api/v1/models
  - POST /api/v1/models/{model_id}/download
  - GET /api/v1/models/jobs/{job_id}
  - DELETE /api/v1/models/{model_id}
  - GET /api/v1/system/info
models: []
test_files:
  - backend/tests/test_paths.py
  - backend/tests/test_registry.py
  - backend/tests/test_downloads.py
  - backend/tests/test_models_api.py
  - apps/frontend/src/hooks/useModels.test.ts
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [huggingface, model-download, dinov2, dinov3, grounding-dino, admin, gated-models]
path: Admin/Models
integration_contracts:
  - function: resolve_model_dir(model_id)
    when: any feature loading model weights from disk — never build a cache path by hand
    applies_to: grounding-dino-annotator, and every Wave 2+ feature that loads a backbone
  - function: ensure_within(root, candidate)
    when: any code turning external input into a filesystem path before read or delete
    applies_to: dataset-store, annotation-workflow, dataset-generator
satisfies_contracts:
  - from: 01-app-shell
    function: get_settings()
    when: any backend module needing configuration
    status: done
    verified_at: "backend/app/api/v1/models.py:67, backend/app/api/v1/system.py:26, backend/app/core/paths.py:37"
  - from: 01-app-shell
    function: apiFetch<T>(path, narrow, init)
    when: any frontend call to a /api/v1/* endpoint
    status: done
    verified_at: "apps/frontend/src/api/models.ts:106,111,115,121,129 — no direct fetch() in this feature"
security_read_sites: []
known_issues:
  - "downloaded_bytes/total_bytes are inflated (observed ~2x) because huggingface_hub creates nested byte-unit tqdm bars per file. The ratio the UI renders is correct and bounded 0-100%; the absolute byte figures should not be trusted for anything but the percentage. Revisit if HF exposes a stable per-file progress hook."
  - "Download jobs live in process memory: restarting the backend loses job history. Intentional (HF's cache resumes the transfer), but the UI shows no in-flight download after a restart until the user retries."
  - "No cancel for an in-flight download; snapshot_download has no cooperative cancellation. Add when the trainer needs job cancellation in Wave 2." 
  - "FIXED 2026-08-19 (Wave 4): snapshot_download fetched the whole repo, including the pickle duplicate of the weights (pytorch_model.bin, *.pt) that this project never loads — the torch.load carve-out is narrow and covers digest-pinned catalogue bytes only. Every model therefore used roughly twice its catalogue estimate: grounding-dino-tiny 1.3 GB against a 690 MB claim, dinov2-small 168 MB against 88 MB, sam2.1-hiera-small 352 MB against 184 MB. Distinct from the tqdm inflation above, which is about reported progress rather than bytes actually fetched. Now excluded via PICKLE_PATTERNS in app/ml/downloads.py, and every catalogue size re-measured from the HF API (safetensors only). Pickles downloaded before the fix are still on disk and must be removed by hand."
sister_projects: []
---

# 02 — Model Manager — Registry, Downloads & Admin Tab

## Purpose

Gets model weights onto the user's disk without shipping them in the installer. A fixed
registry of supported models, a download manager with progress, removal, and the Admin tab
that drives it. Also the one place that knows where weights live — every later feature asks
this module for a path instead of constructing one.

## Architecture

```
Admin tab (React)
  └─ useModels() ── polls ──▶ GET /api/v1/models          catalog + local state
                   ── POST ──▶ /api/v1/models/{id}/download   → job_id (202)
                   ── polls ──▶ /api/v1/models/jobs/{job_id}  → progress
                   ── DELETE ─▶ /api/v1/models/{id}

backend/app/ml/registry.py    the fixed catalog — the ONLY source of downloadable repos
backend/app/ml/downloads.py   job registry + huggingface_hub.snapshot_download in a thread
backend/app/core/paths.py     cache dir resolution + path confinement
```

Downloads run in a worker thread (`snapshot_download` is blocking) and report into an
in-memory job table. Jobs are deliberately not persisted: a download interrupted by a
restart is resumed by HF's own cache, and a stale "downloading" row would lie.

## Data Model

No SQLite yet (that arrives with `03-dataset-store`). Two in-memory structures:

**`ModelSpec`** (static, in `registry.py`)

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Stable slug, e.g. `grounding-dino-tiny`. What the API accepts. |
| `repo_id` | `str` | HuggingFace repo, e.g. `IDEA-Research/grounding-dino-tiny` |
| `kind` | `detector \| backbone` | What the model is for |
| `family` | `grounding-dino \| dinov2 \| dinov3` | Grouping in the UI |
| `gated` | `bool` | True for DINOv3 — needs an accepted licence + `HF_TOKEN` |
| `approx_size_mb` | `int` | Shown before download so the user can judge |
| `description` | `str` | One line for the card |

**`DownloadJob`** (in-memory, `downloads.py`): `job_id`, `model_id`, `state`
(`pending|downloading|complete|failed`), `downloaded_bytes`, `total_bytes`, `message`.

## API Endpoints

### `GET /api/v1/models`
Returns every registry entry plus its local state.
```json
{ "models": [ { "id": "dinov2-base", "repo_id": "facebook/dinov2-base", "kind": "backbone",
  "family": "dinov2", "gated": false, "approx_size_mb": 330,
  "description": "...", "installed": true, "size_on_disk_mb": 331,
  "available": true, "unavailable_reason": null } ] }
```
`available` is false when a gated model has no token; `unavailable_reason` says why.

### `POST /api/v1/models/{model_id}/download` → `202`
`{ "job_id": "...", "model_id": "...", "state": "pending" }`
- `404 not_found` — unknown `model_id`
- `409 conflict` — already installed, or a job for it is running
- `403 forbidden` — gated model and no `HF_TOKEN`

### `GET /api/v1/models/jobs/{job_id}`
`{ "job_id", "model_id", "state", "downloaded_bytes", "total_bytes", "message" }`. `404` if unknown.

### `DELETE /api/v1/models/{model_id}` → `200`
`{ "id": "...", "removed": true, "freed_mb": 331 }`. `404` unknown id; `409` if a download is running.

### `GET /api/v1/system/info`
`{ "device": "mps", "cache_dir": "...", "hf_token_present": true, "free_disk_mb": 128000 }`
Reports **whether** a token is present — never the token.

## Business Rules

- **Only registry models can be downloaded.** `model_id` is looked up in the static
  catalog; the HF repo is never taken from the request. A caller who could name an
  arbitrary repo could write anything anywhere under the cache dir.
- **Every filesystem path is confined** to the cache root via `ensure_within()` before a
  read or delete. This is what stops `../` in an id from reaching outside the cache.
- **Gated models fail with an explanation, not a stack trace.** No token → 403 naming the
  licence page. This is the graceful-fallback answer to the initiative's open question:
  DINOv3 is *offered but marked unavailable*, and DINOv2 stays fully usable without a token.
- **One concurrent job per model.** A second download request while one runs is a 409.
- **The token is read from settings, never logged, never returned.** `/system/info`
  exposes only the boolean.
- **Deleting is confined to the model's own snapshot directory** — never the cache root.

## Data Flow

`installed` — computed in `paths.resolve_model_dir()` (existence + non-empty check on the
cache path) → transported as `ModelInfo.installed` over `GET /api/v1/models` → consumed by
`ModelCard.tsx` to pick Download vs Remove. `size_on_disk_mb` walks the same directory, so
the two can never disagree about which directory they mean.

`device` and `cache_dir` originate in `01-app-shell`'s settings and are re-exposed here via
`/system/info`; the device value is the same `resolved_device` the health probe reports.

## Dependencies

- `01-app-shell` — `get_settings()` for token/cache/device, `apiFetch<T>` for every call,
  the error envelope, and the Admin tab slot this feature fills.

## Security

**Untrusted input:** `model_id` (path parameter) and `job_id`. Both are attacker-controlled
in the sense that anything able to reach loopback can send them.

- `model_id` is **only** ever used as a registry lookup key. It never concatenates into a
  path before that lookup succeeds, so `../../etc` resolves to a 404, not a traversal.
- `ensure_within(root, candidate)` re-checks the resolved path after every join, so a
  future careless caller still cannot escape the cache root. `resolve_model_dir` and the
  delete path both go through it — building a cache path by hand is a contract violation.
- The delete endpoint refuses any target that is not a subdirectory of the cache root, and
  refuses the cache root itself.
- `HF_TOKEN` is passed to `huggingface_hub` and nowhere else: not logged, not in any
  response body, not in an error message. Download failures are reported with the HF error
  class, not the raw exception text, so a token in a URL cannot leak through.

**What this must not expose:** the token, absolute paths outside the cache root, or the
ability to fetch an arbitrary HuggingFace repo.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

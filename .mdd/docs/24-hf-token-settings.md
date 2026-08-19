---
id: 24-hf-token-settings
title: HuggingFace Token & Licence Acknowledgements — The User Supplies Their Own
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [02-model-manager, 23-mask-annotator-registry]
relates: [01-app-shell]
source_files:
  - backend/app/core/env_file.py
  - backend/app/core/config.py
  - backend/app/api/v1/settings.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/settings.ts
  - apps/frontend/src/components/TokenPanel.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/api/models.ts
routes:
  - GET /api/v1/settings/hf-token
  - PUT /api/v1/settings/hf-token
  - DELETE /api/v1/settings/hf-token
  - GET /api/v1/settings/licences
  - POST /api/v1/settings/accepted-licences
models: []
test_files:
  - backend/tests/test_settings_api.py
  - apps/frontend/src/components/TokenPanel.test.tsx
data_flow: writes-existing
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [huggingface-token, secrets, dotenv, licensing, gated-models, admin]
path: Platform/Settings
integration_contracts:
  - function: get_settings.cache_clear()
    when: immediately after any write to the .env file
    note: settings are lru_cached and uvicorn does not reload; without this a saved token is invisible until restart
satisfies_contracts: []
known_issues: []
security_read_sites:
  - backend/app/core/env_file.py — reads and writes the user's .env
  - backend/app/api/v1/settings.py — accepts the token from the request body
---

# 24 — HuggingFace Token & Licence Acknowledgements

## Purpose

Some models are gated by their publisher. **DinoTraining never downloads them on the user's
behalf and never ships a token** — the user supplies their own and starts every download
themselves. This feature gives that token somewhere to live, makes the obligations attached
to a gated model visible rather than implied, and records that the user has read them.

Nothing here is needed for the open path: Grounded SAM, DINOv2 and Grounding DINO all work
without a token, and the panel says so first.

## Two bugs this feature had to fix first

**1. The app was reading no `.env` at all.** `SettingsConfigDict(env_file=".env")` resolves
relative to the *working directory*. The backend runs from `backend/`, so it looked for
`backend/.env`, found nothing, and fell back to defaults for every setting while the real
file sat at the repository root holding all eight keys. Nothing reported it. Writing a token
into that file would have had no effect whatsoever, so the feature is meaningless without
this fix.

The path is now absolute, derived from this module's own location rather than the working
directory, and resolved **at `get_settings()` call time** rather than at class definition —
which is also what lets the cache be cleared and re-read after a write.

**2. The test suite was only accidentally isolated.** `conftest` deleted the environment
variables, but pydantic-settings reads the file regardless. The suite was safe purely
because the resolved path was wrong and no file was found there — fixing bug 1 would have
started feeding a developer's real credentials into every test. `conftest` now points
`DINO_ENV_FILE` at a path that does not exist, making the isolation explicit.

## Architecture

```
core/env_file.py   one resolved .env path; read, write-one-key, mask
core/config.py     get_settings() supplies that path to pydantic-settings
api/v1/settings.py the endpoints — token in, never out
```

`DINO_ENV_FILE` overrides the location. Wave 8 will point it at the per-user config
directory, where a packaged app's writable state belongs; the tests point it at a temporary
file.

## The token never comes back out

This is the feature's central rule:

- **No handler returns the token.** `GET /settings/hf-token` returns `configured`, a masked
  `hint`, the file path, and the accepted-licence list.
- **No log line contains it.** `write_env_value` logs the *key* and the file, never the
  value. The save handler logs "token updated by the user".
- **The masked hint is at most the last four characters**, and a value of eight characters or
  fewer is masked entirely — four characters of an eight-character secret is half of it.
- **The frontend has no state that could hold it.** `TokenPanel` keeps only the user's
  in-progress typing, and clears that on a successful save. There is nothing to load back,
  because the API does not return it.
- Tests assert on the **raw response text**, not a parsed field: a leak would most likely
  appear somewhere nobody thought to parse.

## Writing the file

- **One key is replaced; the rest of the file is untouched.** Rewriting from a parsed dict
  would silently delete the user's comments and reorder their keys. The file is theirs.
- **Written `0600`** — owner read/write only. A token in a world-readable file is a token on
  the floor.
- **`get_settings.cache_clear()` runs immediately after every write.** Settings are
  `lru_cache`d for the process lifetime and uvicorn does not reload, so without this the user
  saves a token and the very next download still reports none — which looks exactly like the
  save having failed silently. This is in `integration_contracts` because it is easy to add a
  second write path and forget it.

## Licence acknowledgements

`GET /settings/licences` returns one notice per gated model, with the explanation text
written **in the backend, beside the `requires_access_request` flag that makes it true or
false**. Putting those sentences in the frontend would let the wording drift away from the
data.

The two texts differ because the two gates differ:

- **Terms only** (DINOv3): accept on the model page, paste a token, access is immediate.
- **Manual approval** (SAM 3): request access *and* accept the licence on the model page,
  paste a token — and a valid token can still be refused until a person at Meta approves it.

`POST /settings/accepted-licences` records that the user was shown the terms and said they
had read them. It is **not** a substitute for accepting them on HuggingFace — only Meta can
grant access. It exists so Wave 8 packaging can state which custom-licensed models a build
has been through.

## API Endpoints

| Method | Path | Notes |
|---|---|---|
| `GET` | `/settings/hf-token` | `configured`, masked `hint`, `env_file`, accepted list |
| `PUT` | `/settings/hf-token` | body `{token}`; `422` for an obviously-wrong value |
| `DELETE` | `/settings/hf-token` | clears it |
| `GET` | `/settings/licences` | one notice per gated model, with explanation text |
| `POST` | `/settings/accepted-licences` | body `{model_id}`; `404` for an unknown model |

Validation is deliberately loose — a minimum length, not a prefix match. HuggingFace has
changed its token prefix before, and rejecting a valid token is worse than accepting a wrong
one, which fails visibly on the next download anyway.

## Frontend

`TokenPanel` sits in the Admin tab above the model grid. It leads with what does *not*
require a token, then the field, then the per-model notices.

The `ModelInfo` type gained `licence`, `licence_url` and `requires_access_request`, and
`ModelFamily` gained `sam2`/`sam3`. `FAMILY_LABELS` is a `Record<ModelFamily, string>`, so
adding a family without a label is a **compile error rather than a section that silently
fails to render** — which is exactly what would have happened to the SAM entries otherwise.

## Security

Accepts a secret from the request body over loopback. Untrusted input is the token string
itself; it is length-checked, written to a `0600` file, and never echoed, logged or
returned. The `model_id` in an acknowledgement is a key into the closed catalogue and a
404 otherwise. No path is ever taken from a caller — the `.env` location comes from
`DINO_ENV_FILE` or the module's own location, never from a request.

## Known Issues

- Only `HF_TOKEN` is editable from the UI. Other `.env` keys are read but must still be
  edited by hand; the panel shows the resolved path so they can be found.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

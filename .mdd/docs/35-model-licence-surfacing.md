---
id: 35-model-licence-surfacing
title: Model Licence Surfacing — Say It Before the Download, Not After
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-6
wave_status: complete
depends_on: [02-model-manager]
relates: [15-head-catalog-import, 24-hf-token-settings, 36-depth-foundation-model]
source_files:
  - backend/app/ml/registry.py
  - backend/app/api/v1/models.py
  - apps/frontend/src/api/models.ts
  - apps/frontend/src/components/ModelCard.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/models
models: []
test_files:
  - backend/tests/test_registry.py
  - apps/frontend/src/components/ModelCard.test.tsx
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [licensing, model-catalogue, admin, packaging, non-commercial, distribution]
path: Admin/Models
integration_contracts:
  - consumer: 36-depth-foundation-model
    function: "ModelSpec(non_commercial=…)"
    when: "any catalogue entry whose licence forbids commercial use"
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "`non_commercial` is a single boolean. Real licences differ in *how* they restrict — non-commercial, research-only, no-redistribution, attribution-required — and Wave 8 may need those apart. One flag is enough while the catalogue holds exactly one restriction shape; splitting it later means revisiting each entry, not rewriting the mechanism."
  - "**Found while building this:** the frontend's `ModelKind` had already drifted — `segmenter` arrived with Wave 4's SAM entries and was never mirrored, and nothing failed because no TypeScript ever assigned one. Realigned here. `FAMILY_LABELS` is `Record<ModelFamily, string>` and *did* work as designed: adding a family forced a label at compile time. The lesson is that a total map catches drift and a bare union does not."
  - "`licence_url` points at the HuggingFace model page rather than the licence text itself. Right for gated models, where that page *is* where you accept it; indirect for an ungated CC BY-NC model where the licence is a well-known document."
sister_projects: []
---

# 35 — Model Licence Surfacing

## Purpose

State every catalogue entry's licence in the admin panel **before** the download is offered,
and flag the ones that forbid commercial use.

## Architecture

Most of the pipe already existed: `ModelSpec.licence` has carried a licence since doc 02,
and `GET /api/v1/models` already returned it. What was missing was the last hop — the model
card never rendered it.

The consequence was specific rather than cosmetic. The licence reached the screen **only for
gated models**, via the token panel's accept-the-terms flow. An **ungated non-commercial**
model — which is exactly the case where not knowing costs something, because nothing stops
you downloading it — showed no licence at all. Wave 6 introduces the first such entry
(Depth Anything V2 Base and Large are CC BY-NC 4.0), which is why this feature runs first.

```
ModelSpec.licence, .non_commercial   (registry.py — the catalogue)
        └─▶ GET /api/v1/models       (already carried licence; now carries the flag)
                └─▶ ModelCard        ← the hop that was missing
```

## Data Model

One new field on `ModelSpec`:

| Field | Type | Default |
|---|---|---|
| `non_commercial` | `bool` | `False` |

`ModelKind` also gains `depth-estimator` and `ModelFamily` gains `depth-anything`, in
preparation for doc 36. Both are additive to closed literals — the pattern doc 22 warned
about applies to SQLite CHECK constraints, not to these, which are validated at import time.

## Business Rules

1. **`non_commercial` is explicit, never inferred from the licence string.** Substring
   matching for "NC" is the same defect as reading a head's capability off its `task`
   label: it works until a licence is worded differently, and it fails **silently in the
   permissive direction** — the one direction that matters when the question is "may I ship
   this?". Two tests state this from both sides: a restrictive licence with no "NC" in it
   must badge, and a permissive one containing those letters must not.
2. **The licence is shown before *and* after installation.** "What did I agree to?" is asked
   more often after the fact than before it.
3. **The licence links out.** A name alone is not a licence; the card links to where it can
   be read.
4. **The non-commercial badge is warning-coloured, not neutral.** It is a constraint on what
   the user may do with the output, not a neutral fact about the file.

## Data Flow

`ModelSpec.non_commercial` → `ModelInfo.non_commercial` (`GET /api/v1/models`) →
`ModelCard`. The frontend type is hand-mirrored, which Wave 4 recorded as drifting silently
twice; `tsc` caught the one stale fixture immediately here because the field is required
rather than optional.

## API Endpoints

`GET /api/v1/models` — unchanged shape plus `non_commercial: bool` on each entry.

## Dependencies

- **02-model-manager** — the catalogue, the download path, and `licence_url`.

## Security

None new. Renders catalogue data the API already served; no new input.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

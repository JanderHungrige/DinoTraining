---
id: 23-mask-annotator-registry
title: Mask Annotator Registry — One Contract, Grounded SAM and SAM 3 Behind It
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [22-mask-dataset-store, 02-model-manager]
relates: [04-grounding-dino-annotator, 08-head-registry]
source_files:
  - backend/app/ml/annotators/__init__.py
  - backend/app/ml/annotators/base.py
  - backend/app/ml/annotators/registry.py
  - backend/app/ml/registry.py
  - backend/app/api/v1/annotators.py
  - backend/app/api/v1/router.py
  - backend/app/datasets/schema.py
  - backend/app/datasets/migrations.py
  - backend/app/datasets/models.py
routes:
  - GET /api/v1/annotators
  - GET /api/v1/annotators/{annotator_id}
models:
  - boxes
  - masks
test_files:
  - backend/tests/test_annotator_registry.py
  - backend/tests/test_annotators_api.py
  - backend/tests/test_migrations.py
  - backend/tests/test_registry.py
data_flow: greenfield
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [mask-annotator, registry, sam3, grounded-sam, licensing, gated-models, provenance]
path: Platform/Annotators
integration_contracts:
  - function: ANNOTATORS registry lookup by id
    when: any code choosing between mask annotators
    note: an `if annotator_id == "sam3"` branch outside this registry is a defect
satisfies_contracts: []
known_issues: []
security_read_sites: []
---

# 23 — Mask Annotator Registry

## Purpose

Wave 4 needs a mask annotator, and there are two of them with very different access stories:
SAM 3 is gated behind Meta's manual approval and a custom licence, while Grounding DINO
composed with SAM 2.1 gives the same result under Apache-2.0 with no gate at all. This
feature defines the single contract both satisfy and the catalogue that describes them, so
everything downstream — the review UI, the dataset writer, the admin tab — picks an
annotator **by id** and never learns which one it got.

## Why a registry and not a flag

The project's standing rule is registries, not enum branches: losses, metrics, decoders,
builders and overlay renderers are all keyed by id. The same reasoning applies harder here,
because the two implementations differ in *availability*, not just behaviour. A boolean like
`use_sam3` would put licence state, gating state, download state and prompting strategy into
one branch, and every consumer would have to re-derive all four.

**An `if annotator_id == "sam3"` outside this module is a defect**, in the same way a
`task ===` comparison in `components/overlays/` is.

## Architecture

```
app/ml/annotators/
  base.py       the MaskAnnotator protocol + MaskProposal (what any annotator returns)
  registry.py   AnnotatorSpec catalogue — id, models needed, licence, gating

app/ml/registry.py   the downloadable-model catalogue, now also carrying licence
                     name and whether a repo needs a manual access request
```

Two catalogue layers, deliberately: an **annotator** is a strategy that may need one model or
several. `grounded-sam` needs *two* (`grounding-dino-tiny` and `sam2.1-hiera-small`);
`sam3` needs one. Collapsing them would make "is this annotator installed?" unanswerable.

## Data Model

### `AnnotatorSpec`

| Field | Notes |
|---|---|
| `id` | `grounded-sam` \| `sam3` |
| `name` | display name |
| `model_ids` | every `ModelSpec.id` that must be installed before this annotator can run |
| `licence` | `Apache-2.0` \| `SAM License` — shown before download, not after |
| `licence_url` | where the licence is actually read |
| `gated` | whether any required model is gated |
| `requires_access_request` | **the SAM 3 distinction** — a token alone is not enough |
| `description` | plain-language, for the admin tab |

### `ModelSpec` additions

`licence: str` and `requires_access_request: bool`. DINOv3 is `gated=True` but
`requires_access_request=False`: accepting its terms is instant. SAM 3 is both, and the
difference is exactly what turns an unhelpful 403 into an actionable message.

Sizes are measured from the HuggingFace API (safetensors only, since the pickle carve-out
means `.pt` is never fetched), not estimated:

| Model | Gated | Licence | Weights |
|---|---|---|---|
| `sam2.1-hiera-small` | no | Apache-2.0 | 184 MB |
| `sam3` | yes, manual | SAM License | 3440 MB |

## Provenance decision

The wave left open whether a Grounded SAM mask needs its own provenance value. **It does.**
`Provenance` already names the specific producer — `grounding-dino`, `hand-drawn`,
`expert-head`, `sam3` — so recording a Grounded SAM mask as `sam3` would be a lie, and
"which masks came from the ungated path" is a real question when comparing annotators.

`grounded-sam` is therefore added, which needs **migration v4**. This is the second use of
the runner built in doc 22 and it exposed a generalisation: the v3 step rebuilt only `boxes`,
but `masks` now carries the same CHECK. The step is therefore rewritten as *"rebuild any
table whose provenance CHECK is out of date"*, driven by the stored DDL — so the next
annotator added costs one entry in `PROVENANCE_VALUES` and no migration code at all.

## API Endpoints

### `GET /api/v1/annotators`

Every annotator with its licence, gating state, required models, and **whether those models
are installed**. This is what lets the admin tab say "Grounded SAM: ready" and "SAM 3: needs
a token and an access request" without the frontend knowing what either one is.

### `GET /api/v1/annotators/{annotator_id}`

One annotator. `404` for an unknown id.

## Business Rules

- **The catalogue is immutable and closed.** A caller names an annotator id; it never supplies
  a repo id. Same reason `app/ml/registry.py` has always refused caller-supplied repos.
- **An annotator is `ready` only when every one of its `model_ids` is installed.** Partial
  installation reports which model is missing, by name.
- **Licence and size are shown before a download is offered, never after.**
- **We never download gated weights on the user's behalf.** The catalogue describes SAM 3 and
  the admin tab offers it; the user triggers it. See `24-hf-token-settings`.

## Data Flow

Greenfield. `GET /api/v1/annotators` reads the two static catalogues plus the installed-model
check that `02-model-manager` already owns, and returns a flat list. No new state.

## Dependencies

- `22-mask-dataset-store` — owns `PROVENANCE_VALUES` and the migration runner this feature
  extends to v4.
- `02-model-manager` — owns the download/installed-state machinery the readiness check reads.

## Security

Accepts external input: an `annotator_id` path parameter. Untrusted, and used only as a dict
key against a closed catalogue — an unknown id is a 404, never a lookup that reaches the
filesystem or the network. No repo id, path or URL is ever accepted from a caller, which is
the invariant that stops loopback access from pulling arbitrary content into the cache.

No secret is read or returned here; the token lives in `24-hf-token-settings`.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

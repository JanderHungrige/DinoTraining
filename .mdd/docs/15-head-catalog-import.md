---
id: 15-head-catalog-import
title: Head Catalogue & Import — Pinned Defaults and Untrusted Community Heads
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-2
wave_status: complete
depends_on: [07-backbone-feature-extractor, 08-head-registry, 09-head-implementations, 12-head-instance-registry]
relates: [02-model-manager, 12-head-instance-registry]
source_files:
  - backend/app/ml/heads/catalog.py
  - backend/app/ml/heads/pretrained.py
  - backend/app/ml/heads/convert.py
  - backend/app/ml/heads/importer.py
  - backend/app/ml/heads/install.py
  - backend/app/ml/heads/register.py
  - backend/app/ml/heads/registry.py
  - backend/app/ml/heads/builders.py
  - backend/app/api/v1/head_catalog.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/headCatalog.ts
  - apps/frontend/src/hooks/useHeadCatalog.ts
  - apps/frontend/src/components/HeadCatalogCard.tsx
  - apps/frontend/src/components/HeadCatalogPanel.tsx
  - apps/frontend/src/components/HeadImportForm.tsx
  - apps/frontend/src/api/headInstances.ts
  - apps/frontend/src/styles.css
  - apps/frontend/src/tabs/AdminTab.tsx
routes:
  - GET /api/v1/head-catalog
  - POST /api/v1/head-catalog/{entry_id}/install
  - POST /api/v1/heads/import
models:
  - head_instances
test_files:
  - backend/tests/test_head_catalog.py
  - backend/tests/test_head_pretrained.py
  - backend/tests/test_head_convert.py
  - backend/tests/test_head_importer.py
  - backend/tests/test_head_catalog_install.py
  - backend/tests/test_head_catalog_api.py
  - backend/tests/test_head_import_api.py
  - backend/tests/head_testkit.py
  - apps/frontend/src/components/HeadCatalogCard.test.tsx
  - apps/frontend/src/components/HeadImportForm.test.tsx
data_flow: .mdd/audits/flow-head-catalog-import-2026-08-18.md
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [safetensors, pickle-safety, sha256-pinning, pretrained-heads, huggingface, provenance, dinov2]
path: Training/Heads
integration_contracts:
  - function: install_catalog_entry(entry_id)
    when: any surface offering a first-party default head
    why: the pinned-digest path is the only sanctioned way a .pth may ever be read
  - function: import_community_head(repo_id, head_type_id, backbone_id)
    when: any surface accepting a user-supplied head source
    why: one validated door for untrusted weights, so no caller can invent a looser one
satisfies_contracts:
  - from: 07-backbone-feature-extractor
    function: read_capabilities(model_id)
    when: before registering or offering any head instance for a backbone
    status: done
    verified_at: "backend/app/ml/heads/install.py:45"
    note: >-
      Also called by importer.py before any network access, and by
      head_catalog.py:113 to attach a compatibility verdict to the listing.
  - from: 08-head-registry
    function: get_head_type(head_type_id)
    when: resolving the task and render hint a catalogue entry installs as
    status: done
    verified_at: "backend/app/ml/heads/register.py:35"
  - from: 08-head-registry
    function: check_compatibility(spec, capabilities)
    when: before offering any head for download or import
    status: done
    verified_at: "backend/app/ml/heads/register.py:43"
    note: >-
      Enforced in register_head for both trust levels; head_catalog.py:134 calls it
      again to build the per-entry explanation shown in the Admin tab.
  - from: 09-head-implementations
    function: build_head(head_type_id, capabilities, num_classes)
    when: constructing the module a downloaded state dict is loaded into
    status: done
    verified_at: "backend/app/ml/heads/register.py:94"
  - from: 12-head-instance-registry
    function: HeadInstanceStore.list_all(task=, backbone=)
    when: deciding whether a catalogue entry is already installed
    status: done
    verified_at: "backend/app/ml/heads/install.py:85"
    note: >-
      head_catalog.py:90 uses the same call to mark installed entries in the listing,
      so "installed" means the same thing here as in every picker.
security_read_sites:
  - backend/app/ml/heads/convert.py — reads a downloaded .pth after digest verification
  - backend/app/ml/heads/importer.py — reads a user-named HuggingFace repo
known_issues:
  - "`linear-depth` (doc 09) is now unreachable as a *usable* head: it is non-trainable and has no weight source, while `dinov2-linear-depth-nyu` provides real depth. Kept deliberately — it is the registry's only test case for the usable-vs-trainable invariant, and deleting it would take that coverage with it."
  - "registry.py is at 293 of the 300-line limit. The next head type added will breach it; split `_SPECS` into its own module at that point rather than trimming the existing comments."
  - "The catalogue pins only dinov2-small/base/large. vitg14 publishes the same three heads upstream but is absent from `app/ml/registry.py`, so it is out of scope until a ViT-g backbone is offered."
  - "WAVE 3 DECISION: install and remove live in different tabs. A default head is installed from the Admin tab's catalogue card but removed from the Head Trainer tab's instance list (`HeadTrainerTab.tsx:103` → `HeadInstanceList.tsx:41`). Backbones get Download *and* Remove on the same Admin card, so heads are inconsistent with models here. Deliberately not resolved in Wave 2: doc 12 makes the instance list the single place heads are presented, and Wave 3's Inference Viewer becomes its third consumer. Decide the affordance once, when all three consumers exist, rather than guessing from two."
  - "Community import accepts only a single-file `model.safetensors` (or the first safetensors by name). A sharded head repo would import only one shard and then fail `load_state_dict(strict=True)` with a missing-keys error rather than an explanation. No such head is known to exist; revisit if one appears."
  - "INTEGRATION-FOUND: the first real install rendered the upstream `.pth` URL inside `HeadInstance.summary`, putting a filename in front of the user in every Wave 3/4 picker — the exact thing doc 12's contract forbids. `source_repo` now holds `facebookresearch/dinov2` and the URL moved to `config.source_url`. The unit test only excluded `.safetensors`, so a `.pth` URL passed; `test_summary_never_shows_a_url_or_filename` now covers schemes and all weight extensions."
  - "INTEGRATION-FOUND: the community import form could never be submitted. `useState(headTypes[0]?.id ?? '')` runs before the async options arrive, so React's controlled value stayed `''` while the `<select>` displayed its first option — the form looked complete and the button was permanently disabled. Fixed by storing only the user's override and falling back to `props[0]`. `HeadImportForm.test.tsx` reproduces the empty-then-populated render sequence, and was confirmed to fail against the old code."
  - "INTEGRATION-FOUND: leaving the Classes field blank (the UI's `auto`) sent `num_classes: null`, which reached `build_head` for a trainable head type and raised an unhandled ValueError — a 500 with the reason only in the log. The count is now inferred from the weight tensor before the head is built, and the import handler has a `ValueError → 422` backstop so no validation failure can surface as a 500 again."
sister_projects: []
---

# 15 — Head Catalogue & Import

## Purpose

Makes heads available **without training them**: first-party pretrained defaults from a
SHA-256-pinned catalogue, and community heads from a HuggingFace repo id. Both take one
code path — fetch, validate against the backbone capability descriptor, register a
`HeadInstance` — because both are the same operation with different trust levels.

This is what makes segmentation and depth useful in Wave 2, before the Annotation Studio
can produce their targets.

## Architecture

```
  first-party (trusted)                    community (untrusted)
  ─────────────────────                    ─────────────────────
  pinned URL + SHA-256                     HuggingFace repo id
        │                                        │
        │  verify digest FIRST                   │  safetensors only
        │  (bytes are known)                     │  .pt/.pth refused outright
        ▼                                        ▼
   torch.load(weights_only=True)          safetensors.load_file()
        │                                        │
        │  remap upstream keys                   │
        └──────────────┬─────────────────────────┘
                       ▼
        validate manifest vs read_capabilities()   ← 07
        check_compatibility(spec, capabilities)    ← 08
        build_head(...) and load_state_dict(strict=True)
                       ▼
        HeadInstanceStore.register(kind=..., source_repo, source_digest)   ← 12
                       ▼
                data/heads/<id>.safetensors
```

**The `.pth` never persists.** It is verified, converted in memory, and written back as
safetensors. After an install completes there is no pickle anywhere in the app's data
directory, so the loader that Waves 3 and 4 use has no pickle branch to reach.

### Why three new head types

The upstream DINOv2 heads do not fit the modules in `09-head-implementations`. Verified
by loading every checkpoint and reading the shapes:

| | upstream | `modules.py` |
|---|---|---|
| classification | `Linear(2·D → 1000)` on `cat([cls, mean(patches)])` | `Linear(D → n)` on `cls` |
| segmentation | `BatchNorm2d(D)` → `Conv2d(D → 150)` | `Conv2d(D → n)`, no norm |
| depth | `Conv2d(2·D → 256)` bins → weighted sum | `Conv2d(D → 1)` scalar |

Forcing the weights into the existing modules would load cleanly and emit garbage. So
the catalogue registers **three new head types** whose modules mirror upstream exactly.
That is precisely what `08`'s "a head type is a registry entry, never an enum branch"
contract exists for — adding them touches the registry and the builder table, and no
training or inference code at all.

| New head type | Task | Trainable | Classes |
|---|---|---|---|
| `dinov2-linear-classifier-in1k` | classification | no | 1000 (ImageNet-1k) |
| `dinov2-linear-segmenter-ade20k` | segmentation | no | 150 (ADE20k) |
| `dinov2-linear-depth-nyu` | depth | no | — (256 bins → metres) |

All three are `trainable=False`: they are fixed-vocabulary heads for someone else's
label set, so fine-tuning them here is meaningless. `trainable_head_types()` already
excludes them, which keeps them out of the trainer without a single new condition.

All three declare `compatible_families=frozenset({"dinov2"})`, so selecting a DINOv3
backbone produces the explained refusal `check_compatibility` already generates rather
than a greyed-out row.

## Data Model

### `CatalogEntry` (frozen dataclass, static table)

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | `<head-type-id>.<backbone-id>`, e.g. `dinov2-linear-depth-nyu.dinov2-base` |
| `head_type_id` | `str` | Resolved through `get_head_type` |
| `backbone_id` | `str` | Registry key — a head file is per backbone size |
| `url` | `str` | Pinned absolute URL. Never assembled from caller input |
| `sha256` | `str` | Verified before the file is read |
| `size_bytes` | `int` | Shown before the user commits to a download |
| `num_classes` | `int \| None` | 1000 / 150 / None |
| `embed_dim` | `int` | Asserted against `read_capabilities().embed_dim` |
| `trained_on` | `str` | Provenance string, e.g. `"ADE20k, 150 classes"` |
| `licence` | `str` | `"Apache-2.0"` for every current entry |
| `depth_range` | `tuple[float, float] \| None` | `(0.001, 10.0)` for NYU, else `None` |

Nine entries: three tasks × `dinov2-small` / `dinov2-base` / `dinov2-large`.

**Digests are pinned in source**, each verified by downloading the real file:

```
dinov2_vits14_linear_head.pth         74d2e1e9…  3 077 159 B
dinov2_vits14_ade20k_linear_head.pth  67e10225…    719 673 B
dinov2_vits14_nyu_linear_head.pth     6062f678…  2 367 211 B
… (base and large likewise)
```

### DINOv3: deliberately absent

There is no DINOv3 entry, and this is a finding rather than an omission. Meta publishes
DINOv3 heads only for **ViT-7B/16** (not the ViT-B/16 or ViT-L/16 this app ships), gated
behind a per-user e-mailed URL list, under the DINOv3 License rather than Apache-2.0.
None of the three conditions can be met, so DINOv3 backbones are train-your-own only.
The catalogue says so in the UI instead of showing an empty list.

## API Endpoints

### `GET /api/v1/head-catalog?backbone=<id>`

Every entry with its install state and, when `backbone` is given, its compatibility
verdict and reason.

```json
{
  "entries": [
    {
      "id": "dinov2-linear-segmenter-ade20k.dinov2-small",
      "title": "Linear segmenter (ADE20k)",
      "task": "segmentation",
      "backbone_id": "dinov2-small",
      "trained_on": "ADE20k, 150 classes",
      "licence": "Apache-2.0",
      "size_bytes": 719673,
      "installed": false,
      "installed_instance_id": null,
      "backbone_installed": true,
      "compatible": true,
      "incompatible_reason": null
    }
  ]
}
```

`compatible` is `null` unless `?backbone=` was supplied, matching `GET /head-types`.

### `POST /api/v1/head-catalog/{entry_id}/install`

Downloads, verifies, converts and registers. Returns the created `HeadInstanceInfo`.

| Status | When |
|---|---|
| `201` | installed; body is the new head instance |
| `404` | unknown `entry_id` |
| `409` | backbone not installed — download it first |
| `409` | already installed (idempotency is *not* implied; the user gets told) |
| `422` | digest mismatch, or shapes disagree with the backbone descriptor |
| `503` | the upstream host was unreachable |

### `POST /api/v1/heads/import`

```json
{ "repo_id": "someone/dinov2-linear-probe", "head_type_id": "linear-classifier",
  "backbone_id": "dinov2-base", "name": "Custom probe" }
```

| Status | When |
|---|---|
| `201` | imported; body is the new head instance |
| `400` | `repo_id` is not a valid `owner/name` |
| `404` | repo or `model.safetensors` not found |
| `409` | backbone not installed |
| `415` | the repo has no safetensors — refused, with the reason |
| `422` | manifest disagrees with the backbone, or tensor shapes do not match |

## Business Rules

- **A caller never supplies a URL.** First-party installs name a catalogue key; the URL
  comes from the static table. This is `02-model-manager`'s rule, applied to heads.
- **Digest before read.** The SHA-256 is checked against the downloaded bytes *before*
  `torch.load` touches them. This ordering is the entire safety argument for the pickle
  carve-out: we are not trusting the host, we are trusting bytes we can verify.
- **`weights_only=True`, always.** Even for pinned files. The DINOv2 depth checkpoints
  embed a numpy scalar, so loading needs `numpy.core.multiarray.scalar` and the numpy
  dtype constructors added to torch's allowlist — a fixed, named list, never
  `weights_only=False`. See Known Issues for why this needs an alias.
- **Community imports are safetensors or nothing.** A repo containing only `.pt`/`.pth`
  is refused with an explanation. There is no "prefer safetensors, fall back to pickle"
  branch, because a fallback is reachable by anyone who can name a repo.
- **`repo_id` is validated as `owner/name`** — no path separators beyond the single
  slash, no `..`, no scheme. It is passed to `hf_hub_download`, never joined onto a path.
- **Shapes are checked against the descriptor, not assumed.** `embed_dim` from
  `read_capabilities` must match the entry, and `load_state_dict` runs `strict=True`. A
  head whose tensors merely *load* is the failure mode this whole feature guards against.
- **Incompatibility is explained.** Every refusal names the reason and, where one exists,
  which installed backbone the head *would* work with.
- **Provenance is mandatory.** Every registration passes `source_repo` and
  `source_digest`; `kind` is `pretrained-default` for catalogue entries and `community`
  for imports. Waves 3 and 4 read those to present the head.

### Upstream details that must be preserved exactly

- **Concat order differs between the two `2·D` heads.** Classification is
  `cat([cls, mean(patches)])` — CLS first. Depth is `cat([patches, cls.expand])` —
  patches first. Both read from DINOv2 source; swapping either yields correctly-shaped,
  silently wrong output.
- **Depth decoding** is `relu(logits) + 0.1`, normalised over the bin axis, then a dot
  product with `linspace(0.001, 10.0, 256)`. The range is NYU's and lives in the
  catalogue entry, not in the module.
- **Convolve then upsample.** Upstream resizes features 4× before a 1×1 conv; a 1×1 conv
  is pointwise-linear and bilinear resize is linear, so the operations commute. Doing the
  conv first is identical and resizes 256 channels instead of 2·D.

## Data Flow

See `.mdd/audits/flow-head-catalog-import-2026-08-18.md` for the full trace, the verified
state-dict shapes, and the upstream-source citations behind the rules above.

## Dependencies

- `07-backbone-feature-extractor` — `read_capabilities`, `BackboneFeatures`
- `08-head-registry` — `get_head_type`, `check_compatibility`, the spec table this extends
- `09-head-implementations` — `build_head`, the builder-table contract
- `12-head-instance-registry` — `HeadInstanceStore.register`, `list_all`

## Security

This is the app's **only** untrusted-input boundary for model weights, and the only place
a pickle is ever read.

**Untrusted inputs:** `repo_id` (arbitrary string from the user), and everything inside
the repo it names — tensor names, shapes, dtypes, file list, `config.json`.

**What a malicious caller could attempt:**

| Attempt | Defence |
|---|---|
| Import a `.pth` to get `torch.load` RCE | safetensors only; pickle rejected before download |
| `repo_id` as `../../etc/passwd` or a URL | validated as `owner/name`; passed to the HF client, never to a path join |
| Oversized tensors to exhaust memory | file size checked against a ceiling before load |
| Tensor names colliding with a trained head | weights are re-saved under a fresh uuid by `12`; names never reach the filesystem |
| Manifest claiming a mismatched backbone | `read_capabilities` is authoritative; the manifest is only ever *checked*, never trusted |

**What this feature is not permitted to expose:** the HF token (used for gated
downloads, never echoed — download errors report the exception class, following
`downloads.py`), the cache path layout, or any upstream error text that may embed a
signed URL.

**The pickle carve-out, stated precisely:** `torch.load` runs on exactly one code path —
a file whose SHA-256 already matched a digest compiled into the binary. The pickle path
is not reachable from any user-supplied value. If the digest check is ever moved after
the load, that property is gone.

## Known Issues

See the `known_issues` list in the frontmatter. Three of them were found only by driving
the running app — none of the 581 backend or 133 frontend tests caught them, and all
three were the same shape: a value that is *structurally* valid but wrong in context (a
URL where a description belongs, an empty controlled-select value, a null class count).

## Bugs

(none yet — populated by /mdd bug when issues are reported)

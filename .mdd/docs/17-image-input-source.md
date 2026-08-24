---
id: 17-image-input-source
title: Image Input Source — One Image or a Folder, Behind One Contract
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-3
wave_status: complete
depends_on: [16-inference-engine]
relates: [04-grounding-dino-annotator, 06-annotation-workflow, 19-side-by-side-viewer]
source_files:
  - backend/app/ml/inference/source.py
  - backend/app/api/v1/inference.py
  - apps/frontend/src/api/inference.ts
  - apps/frontend/src/lib/dialog.ts
  - apps/frontend/src/hooks/useImageSource.ts
  - apps/frontend/src/components/ImageSourcePicker.tsx
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/inference/source
models: []
test_files:
  - backend/tests/test_inference_source.py
  - backend/tests/test_inference_api.py
  - apps/frontend/src/hooks/useImageSource.test.ts
  - apps/frontend/src/components/ImageSourcePicker.test.tsx
data_flow: .mdd/audits/flow-image-input-source-2026-08-18.md
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [inference, input-source, folder-listing, image-io, tauri-dialog, item-identity]
path: Inference/Input
integration_contracts:
  - function: GET /api/v1/inference/source?path=
    when: any surface that needs the images a user pointed at
    why: one place decides what counts as a usable input, for a file and a folder alike
  - function: useImageSource(path)
    when: any viewer that steps through the user's chosen input
    why: the sequencing contract feature 19's viewer consumes; a video source must satisfy
      this same shape without the viewer changing
satisfies_contracts: []
  # Doc 16 publishes run_inference / Prediction as contracts for "any surface that needs a
  # head's prediction". This feature is upstream of that: it produces the `image_path` the
  # endpoint consumes and never calls it. Claimed by 19-side-by-side-viewer and
  # 20-inference-overlay-render instead. Recorded rather than claimed, following doc 16's
  # own handling of doc 12's list_all — an entry naming a function this feature never calls
  # is worse than no entry.
security_read_sites:
  - "backend/app/ml/inference/source.py:60 — resolve_source() reads a user-supplied path"
known_issues:
  - "`GET /api/v1/annotate/folder` (Wave 1) and `GET /api/v1/inference/source` both list a folder through `list_images`. Deliberate — different questions, different consumers — but a *third* consumer means migrating the Wave 1 endpoint onto this shape and deleting it, not adding a variant."
  - "A folder over `MAX_ITEMS` (1000) is truncated and the viewer says so, but there is no paging. If real folders hit this, paging belongs in this feature, not in the viewer."
  - "The viewer loads image bytes through `imageUrl()` from the *annotate* API slice (`GET /api/v1/annotate/image`). One implementation is right; the naming is not. When 19-side-by-side-viewer lands, promote that endpoint out of the annotate slice rather than duplicating it."
sister_projects: []
---

# 17 — Image Input Source

## Purpose

The user points the Inference Viewer at **a single image or a folder of images**, and gets
back a sequence of items to step through. This feature owns that resolution and nothing
else — it does not run a model and does not draw anything.

The real deliverable is **the contract**, not the file listing. Feature 19's viewer consumes
it, and the deferred video source must be able to satisfy it later without the viewer
changing. So the shape is *"something that yields images one at a time under a stable
identity"*, not *"a list of paths"*.

## Architecture

```
user picks a path (native dialog under Tauri, or types it)
        │
        │  GET /api/v1/inference/source?path=…
        ▼
resolve_source(path)                        backend/app/ml/inference/source.py
        │
        ├─ is a file   → read_image() to confirm it is one  → 1 item
        └─ is a folder → list_images()  (non-recursive)     → N items
        │
        ▼
InputSource { kind, root, items[ InputItem{ item_id, name, path } ], truncated }
        │
        ▼
useImageSource(path)      ← index, current, next/previous, count
        │
        ▼
feature 19's viewer   →   POST /api/v1/inference  { image_path: current.path, … }
```

Both branches go through `app/ml/images.py`, which Wave 1 wrote and which already owns the
"a file PIL opens as one of a small set of formats" narrowing. **No second file-reading
path is introduced.**

## Data Model

### `InputItem` (frozen dataclass)

| Field | Type | Notes |
|---|---|---|
| `item_id` | `str` | 16 hex chars of `sha256(absolute path)`. Stable across re-listing. |
| `name` | `str` | The filename — what the user is shown. |
| `path` | `Path` | Absolute, resolved. What `POST /inference` and the image endpoint take. |

### `InputSource` (frozen dataclass)

| Field | Type | Notes |
|---|---|---|
| `kind` | `"file" \| "folder"` | What the user picked, so the UI can say it back to them. |
| `root` | `Path` | The file itself, or the folder. |
| `items` | `tuple[InputItem, ...]` | Sorted; empty is legal for a folder with no images. |
| `truncated` | `bool` | `True` when the folder held more than `MAX_ITEMS`. |

### Why `item_id` and not the path

The path is already unique, so uniqueness is not the reason. The reason is that a stable,
**path-free** identity is the only part of this contract a future video source can also
produce. Everything keyed on `item_id` — React list keys, a per-item result map, feature 18's
backbone-feature cache — keeps working when items stop being files. Keying on the path would
bake "an item is a file" into every consumer, which is precisely what this feature exists to
prevent.

`path` remains on the item because doc 16 made inference path-based on purpose. A video
source materialises frames to disk (which Wave 4's dataset generator does anyway) rather
than forcing a second byte-transport contract.

## API Endpoints

### `GET /api/v1/inference/source?path=<absolute path>`

Response `200`:

```json
{
  "kind": "folder",
  "root": "/Users/you/photos",
  "items": [{ "item_id": "9f2c…", "name": "cat.png", "path": "/Users/you/photos/cat.png" }],
  "truncated": false
}
```

| Status | When |
|---|---|
| `200` | resolved — including a folder that contains no images (`items: []`) |
| `404` | the path is neither an existing file nor a folder |
| `415` | the path is a file that is not a readable image |
| `422` | empty `path` parameter |

**An empty folder is `200`, not `404`.** "This folder has no images in it" is a normal thing
for a user to discover, and the viewer needs to say so; an error status would push a routine
outcome down the failure path.

## Business Rules

- **Listing is non-recursive.** Inherited deliberately from `list_images`: pointing this at
  `/` must enumerate one level, not walk the user's disk.
- **A single-file source is validated by opening it.** The extension is a hint, never the
  check — same rule as every other read in the app. That costs one decode, which is
  acceptable for one file and is *not* done per entry of a folder listing (see below).
- **Folder entries are not opened during listing.** `list_images` filters by suffix only. A
  corrupt file in a photo folder therefore appears in the list and fails when it is
  *selected*, with a 415 from the image or inference endpoint. Opening thousands of files to
  pre-validate them would make picking a folder take seconds and would still be stale by the
  time the user got there.
- **`MAX_ITEMS = 1000`, with `truncated: true` when it bites.** A silent cap is worse than
  no cap: the user must be able to tell "this folder has 1000 images" from "you are seeing
  the first 1000 of 5000".
- **Items are sorted** — `list_images` already sorts, and a stable order is what makes
  "next" mean anything.
- **The hook never seeds state from async data.** `useImageSource` stores an index and
  derives the current item; it does not `useState(items[0])`. That is the CLAUDE.md rule
  Wave 2 broke twice.

## Data Flow

See `.mdd/audits/flow-image-input-source-2026-08-18.md`.

## Dependencies

`16-inference-engine` — this feature produces the `image_path` that endpoint consumes. It
is **upstream** of doc 16's contracts rather than a consumer of them: nothing here calls
`run_inference`, so `satisfies_contracts` is deliberately empty and those contracts are
claimed by features 19 and 20, where a head is actually run. This mirrors doc 16's own
handling of doc 12's `list_all`.

Wave 1's `app/ml/images.py` is reused directly rather than depended on as a documented
feature; it is infrastructure, not a contract-bearing feature.

## Security

Accepts **one user-supplied filesystem path** and reads it. Confinement is not the control
here and never has been in this app: the user genuinely does point it at arbitrary folders
on their own machine, so a root-jail would break the product. The control is the same
narrowing Wave 1 established — a path is only ever read *as an image*, through
`read_image`'s format allowlist, and a directory is only ever enumerated one level deep.

What this feature must never do, and does not:

- return anything about a non-image file (they are filtered out, not reported)
- follow the path anywhere the user did not name (no globbing, no recursion, no symlink
  chasing beyond what `resolve()` does on the user's own path)
- put the path in an error message the UI shows verbatim without it having come from the
  user in the first place

The listing endpoint is `GET` with the path as a query parameter. This mirrors Wave 1's
`/annotate/folder` exactly, and the path is the user's own local directory rather than
personal data leaving the machine — it does not leave loopback.

## Known Issues

- `GET /api/v1/annotate/folder` (Wave 1) and `GET /api/v1/inference/source` both list a
  folder through `list_images`. Two endpoints over one helper is deliberate — they answer
  different questions and have different consumers — but if a **third** consumer appears,
  the Wave 1 endpoint should be migrated onto this shape and deleted rather than a third
  variant added.
- A folder with more than `MAX_ITEMS` images is truncated. The viewer surfaces the flag but
  offers no paging; if real folders hit this, paging belongs here, not in the viewer.
- The tab loads image bytes through `imageUrl()` from the **annotate** API slice
  (`GET /api/v1/annotate/image`). One implementation is right; the naming is not. When
  `19-side-by-side-viewer` lands, promote that endpoint out of the annotate slice rather
  than duplicating it.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

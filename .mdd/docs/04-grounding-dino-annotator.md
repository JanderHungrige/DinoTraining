---
id: 04-grounding-dino-annotator
title: Grounding DINO Annotator — Prompted Box Proposals
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-1
wave_status: complete
depends_on: [02-model-manager, 03-dataset-store]
relates: [06-annotation-workflow]
source_files:
  - backend/app/ml/images.py
  - backend/app/ml/detector.py
  - backend/app/api/v1/annotate.py
routes:
  - POST /api/v1/annotate
  - GET /api/v1/annotate/folder
  - GET /api/v1/annotate/image
models: []
test_files:
  - backend/tests/test_images.py
  - backend/tests/test_detector.py
  - backend/tests/test_annotate_api.py
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [grounding-dino, zero-shot-detection, inference, prompts, thresholds, pytorch]
path: Studio/Annotation
integration_contracts:
  - function: load_detector(model_id)
    when: any feature needing Grounding DINO — never construct the pipeline inline
    applies_to: dataset-generator (Wave 4)
  - function: list_images(folder) / read_image(path)
    when: any feature reading user-chosen image files
    applies_to: annotation-workflow, dataset-generator
satisfies_contracts:
  - from: 02-model-manager
    function: resolve_model_dir(model_id)
    when: loading weights from disk — never build a cache path by hand
    status: done
    verified_at: "backend/app/ml/detector.py:89 — load_detector(); no hand-built cache path"
  - from: 01-app-shell
    function: get_settings()
    when: any backend module needing configuration
    status: done
    verified_at: "backend/app/ml/detector.py:81 — resolved_device for model placement"
security_read_sites:
  - "backend/app/ml/images.py — list_images() and read_image() open user-supplied paths"
known_issues:
  - "Fixed during this feature: is_installed() treated any non-empty directory as installed, so a model read as Installed the moment snapshot_download wrote config.json while ~690MB of weights were still downloading. Now requires a weights file (see paths.WEIGHT_SUFFIXES)."
  - "The detector cache is never evicted; loading both grounding-dino-tiny and -base holds ~2GB of weights for the process lifetime. Add an LRU or an explicit unload when Wave 3 loads backbones alongside detectors."
  - "First inference pays model load (several seconds) inside the request. Acceptable for Wave 1; consider warming the detector when the Studio tab opens."
  - "list_images() is non-recursive by design; a user with nested photo folders must pick each one. Revisit with the folder picker UX in Wave 4."
sister_projects: []
---

# 04 — Grounding DINO Annotator — Prompted Box Proposals

## Purpose

Turns "a cat" plus a folder of images into box proposals the user can accept or
reject. This is the only place in Wave 1 that runs a model, and the only place that
reads image files the user picked from outside the app's own directories.

## Architecture

```
POST /api/v1/annotate  { image_path, prompt, box_threshold, text_threshold, model_id }
     │
     ├─ images.read_image()      validate + decode (PIL), get real dimensions
     ├─ detector.load_detector() cached per (model_id, device); weights from
     │                           resolve_model_dir() — never a hand-built path
     └─ AutoModelForZeroShotObjectDetection → boxes in absolute pixels
```

The model is loaded once and cached per process. Loading Grounding DINO takes seconds
and hundreds of MB; doing it per request would make the annotation loop unusable.

Boxes come back in the **same convention the dataset store uses** — absolute pixels,
top-left origin, `[x, y, w, h]`. The conversion from the model's `xyxy` output happens
once, here, so nothing downstream has to guess which convention it is holding.

## API Endpoints

### `POST /api/v1/annotate`
```json
{ "image_path": "/Users/me/pics/a.jpg", "prompt": "a cat. a dog.",
  "box_threshold": 0.3, "text_threshold": 0.25, "model_id": "grounding-dino-tiny" }
```
Response:
```json
{ "image_path": "...", "width": 1920, "height": 1080, "prompt": "a cat. a dog.",
  "device": "mps", "boxes": [
    { "label": "positive", "provenance": "grounding-dino", "x": 10, "y": 20,
      "w": 100, "h": 80, "score": 0.91, "text": "a cat" } ] }
```
- `404` — image not found, or the model is not installed (message says which)
- `400` — path is not a decodable image
- `422` — blank prompt, or a threshold outside 0–1

Proposals arrive labelled `positive` because that is what the detector is asserting;
the user's job is to downgrade the wrong ones. Defaulting to `unclear` would mean
every correct box needs a click, which is the wrong side of the effort trade.

### `GET /api/v1/annotate/folder?path=...`
Lists decodable images in a folder (non-recursive). `404` if absent, `400` if not a
directory.

### `GET /api/v1/annotate/image?path=...`
Streams the image bytes so the canvas can render a local file the webview cannot
otherwise reach.

## Business Rules

- **The model must already be installed.** No implicit download: a 690 MB fetch
  triggered by a keystroke in the Studio is not something to do silently. A missing
  model is a 404 telling the user to install it in the Admin tab.
- **Thresholds are validated 0–1** and default to 0.3 (box) / 0.25 (text), the values
  the Grounding DINO authors use in their own examples.
- **The prompt is passed through as written.** Grounding DINO expects lowercase
  phrases separated by periods; the endpoint normalises trailing punctuation but does
  not rewrite the user's wording, because silently editing a prompt makes tuning it
  impossible.
- **An image that fails to decode is a 400, not a 500** — a stray `.txt` in a photo
  folder is expected input, not an internal error.
- **Inference runs in a worker thread** so a slow CPU-bound forward pass does not
  block the event loop and stall the health probe.

## Data Flow

`score` — produced by the model's post-processing in `detector.detect()` → transported
as `ProposedBox.score` over `POST /api/v1/annotate` → carried unchanged into
`dataset-store` when the user saves, where it lands in `boxes.score`. The same float
survives the whole path, so a later "why was this proposed?" is answerable.

## Dependencies

- `02-model-manager` — `resolve_model_dir()` for weights, and the install state that
  decides whether this endpoint can run at all.
- `03-dataset-store` — reuses `Box`/`Label`/`Provenance` so a proposal is already the
  shape the save endpoint accepts; no translation layer between propose and store.

## Security

**Untrusted input:** `image_path`, `folder`, `prompt`, thresholds.

This feature reads files the user chose, which by design lie outside the app's own
directories — so path confinement is not the applicable control here. The controls are:

- **CORS preflight is the CSRF boundary.** A malicious page could otherwise POST to
  loopback and probe the filesystem. `application/json` is not a CORS-simple content
  type, so the browser sends a preflight, and `01-app-shell` allows only the Tauri and
  Vite dev origins. This is why the annotate endpoints take JSON bodies and query
  params under an `Accept: application/json` contract rather than form encodings.
- **Reads are restricted to decodable images.** The path must be an existing regular
  file that PIL can open and whose format is in an allowlist. That reduces "read any
  file" to "confirm a file is a valid image", and the response carries boxes and
  dimensions — never file bytes from an arbitrary path.
- **Directory listing is non-recursive** and returns only image files, so pointing it
  at `/` enumerates one level rather than walking the user's disk.
- **Errors do not echo the path back verbatim** into a message that could be rendered
  as HTML; the frontend renders text nodes, and the envelope carries a code.

**What this must not expose:** file contents of non-image files, directory trees, or
the ability to make the backend fetch a remote URL (paths are local-only; no scheme is
accepted).

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

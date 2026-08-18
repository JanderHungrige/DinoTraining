# Wave 3 handoff — COMPLETE (6 of 6)

**Branch:** `feat/dinotraining-wave-3` — pushed, **10 commits ahead of `dev`, not merged**
**Date:** 2026-08-18
**Tests:** 672 backend (`pytest`), 207 frontend (`vitest`). ruff, mypy, tsc all clean.

Wave 3 delivered the **Inference Viewer**: pick an image or a folder, pick one or more
heads, see original vs. annotated results side by side, and compare several heads on the
same task. Still images only — video was deliberately deferred.

## Waiting on Jan — do not do these unasked

1. **Merge to `dev`.** Jan merges himself. He delegated the Wave 2 merge explicitly and
   that does **not** generalise. Ask.
2. **Confirm the demo-state.** The wave is not "done" until he can demonstrate it himself.
   It has been driven end to end in the app, but that is not the same thing.
3. **Delete `.mdd/jobs/wave-dinotraining-wave-3/`** once he confirms. MDD's PE4 deletes the
   job folder on confirmation; it is ephemeral tracking and was left in place on purpose.
4. **Plan Wave 4** (`/mdd plan-wave dinotraining-wave-4`), and **confirm where live
   video/webcam lands**. Wave 4 (Dataset Generator) is the *proposed* home because it
   already ingests new imagery and a frame is just another source — proposed, never agreed.

## If you are in a fresh environment (claude.ai/code, a remote agent, a new machine)

The repo holds **no model weights and no venv** — both gitignored.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest tests/ -q          # expect 672 passing
cd ../apps/frontend && npm install --legacy-peer-deps && npx vitest run   # expect 207
```

Then real weights — ungated, Apache-2.0, ~174 MB:

```bash
# with the backend running on 127.0.0.1:8756
curl -X POST http://127.0.0.1:8756/api/v1/models/dinov2-small/download   # 168 MB
# poll /api/v1/models/jobs/{job_id} until state=complete, then:
curl -X POST http://127.0.0.1:8756/api/v1/head-catalog/dinov2-linear-classifier-in1k.dinov2-small/install
curl -X POST http://127.0.0.1:8756/api/v1/head-catalog/dinov2-linear-segmenter-ade20k.dinov2-small/install
curl -X POST http://127.0.0.1:8756/api/v1/head-catalog/dinov2-linear-depth-nyu.dinov2-small/install
```

Head instance ids are generated per install, so they will **not** match the ones below —
read them from `GET /api/v1/heads`. On this machine today:

```
08ab54602f614a5f861cc64346ba1789   classification (IN1k, 1000 classes)
a81053b637a542d8923e38434120555d   segmentation   (ADE20k, 150 classes)
313c37d38a0844e2a39d61f94555e1be   depth          (NYUd, metres)
```

**Confirm the bootstrap before building on it** with the smoke test below.

## Smoke test — free, no training

Recreate the panorama: a 900×300 image with an object at x=770–880, i.e. exactly the region
a centre crop destroys.

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"image_path":"/abs/path.png","backbone_id":"dinov2-small","instance_ids":["<cls>","<seg>","<depth>"]}' \
  http://127.0.0.1:8756/api/v1/inference/compose
```

Expect **`passes: 2`** for those three heads (two framings, not three), and grids `[16,16]`
and `[32,32]`.

**Read the result correctly.** *Depth* is the head that proves letterbox + inversion: that
far-right region reads clearly different from the background. The **ADE20k segmenter does
not distinguish it** on a synthetic flat-colour panorama — it returns two classes and the
object is not one of them. That is the model on unnatural input, not a bug, and it is
recorded in doc 20. Do not "fix" it.

## What Wave 3 built

| # | Feature | Doc | The load-bearing idea |
|---|---|---|---|
| 1 | inference-engine | [16](docs/16-inference-engine.md) | predictions in **original image coordinates**, tagged with `render_hint` |
| 2 | image-input-source | [17](docs/17-image-input-source.md) | one image and a folder are **the same shape**, items keyed by an opaque `item_id` |
| 3 | multi-head-compose | [18](docs/18-multi-head-compose.md) | N heads, **one pass per framing**; cache key `(backbone_id, geometry, size)` |
| 4 | side-by-side-viewer | [19](docs/19-side-by-side-viewer.md) | **one transform rendered N times** — panes cannot drift |
| 5 | inference-overlay-render | [20](docs/20-inference-overlay-render.md) | dispatch on `render_hint` via a `Record`; dense maps travel as **PNG** |
| 6 | same-task-head-compare | [21](docs/21-same-task-head-compare.md) | comparison is **a filtered list, not a mode** |

## Architecture later waves must honour

- **Heads are registry entries, not enum branches.** Losses, metrics, decoders, builders,
  and now **overlay renderers** are registries keyed by id. `OVERLAY_RENDERERS` is
  `Record<RenderHint, …>` on purpose: adding a hint without a renderer is a compile error,
  not a blank pane. A `task ===` comparison in `components/overlays/` is a defect.
- **Two backbone passes, not one per task.** `consumes` is **not** in the cache key — `cls`
  and `patches` come from the same `BackboneFeatures`. One pass cannot be synthesised from
  another. The cache lives in the compose call and dies with it; a cross-call cache needs an
  invalidation answer (mtime) nobody has needed yet, and would show up as `passes: 0`.
- **Dense maps travel as base64 PNG** (`mask_png` / `depth_png`), never nested JSON lists.
  Measured: 12.5 MB → 17 KB for a 3000×2000 segmentation, because the map is upsampled from
  a 32×32 grid and PNG removes exactly that redundancy. The pixel value is *data* (a class
  index, or 0..255 depth) — no palette is baked in, so the client owns colour.
- **Usable ≠ trainable**, and **provenance is the cross-tab contract** — `HeadInstance.summary`,
  never a filename. Wave 2 shipped one bug from breaking this; Wave 3 has three consumers of
  it now.
- **The pickle carve-out stays narrow:** one `torch.load`, on digest-pinned bytes only.
- **Preprocessing is derived from (backbone, head)**, never configured by a caller.
- SAM lands in **Wave 4**, making segmentation trainable in-app.

## Gotchas (all still live)

- **Restart the dev server after backend edits** — uvicorn does not reload. `preview_stop`
  then `preview_start`. Stale Vite HMR errors persist in the browser console **across a
  restart and a reload**, and name files you never touched. Verify with `tsc` + `read_page`,
  not the console.
- **`git commit -m` with quotes breaks under zsh**, and `git merge -F -` does not accept
  stdin. Write the message to a file and use `-F <file>`.
- **A 300-line hook blocks writes.** It fired twice this wave. `registry.py` is at 293 and
  `preprocess.py` at 259 — the next addition to either needs a split, not a trim.
- **Do not use `perl -pi -e 's|…|…|'` with `|` as the delimiter** on regexes containing `|`.
- **No prettier config; single quotes.** Do not run prettier.
- **MDD hashes** must be recomputed after any initiative/wave edit or the next
  `plan-execute` hard-stops. Feature docs carry no hash.
  ```bash
  f=.mdd/waves/dinotraining-wave-4.md
  new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
  perl -pi -e "s/^hash: .*/hash: $new/" "$f"
  ```

## Testing lessons this wave — the bugs the suite could not see

Every real bug again came from driving the app, never from the suite. Three new shapes:

1. **CPU-only tests over an MPS runtime.** `.numpy()` raises on any tensor that is not a
   plain CPU leaf. All 668 tests passed while every dense prediction 500'd, because every
   test builds tensors on the CPU. → route device→host through one
   `.detach().cpu().numpy()` helper; pair a `@skipif` MPS test with a **deterministic**
   `requires_grad` one.
2. **Geometry measured against the wrong element.** jsdom reports every element as `0×0`, so
   a clamp against the wrong box behaves exactly like one against the right box. → stub
   `HTMLElement.prototype.clientWidth/Height` **before mount** (measurement happens in a
   mount effect) and assert the **exact** boundary value — a loose assertion passes at 0.
3. **A handler on an outer container catching a bubbled event** from a control inside it
   (double-clicking "Zoom in" reset the view).

**Always confirm a regression test fails against the old code.** One written this wave was
vacuous and passed either way until it was rewritten.

## Known issues worth picking up

- **The ImageNet classifier ships no class names**, so results render as `class 416` rather
  than `Siamese cat`. The head is close to unreadable in the UI. The 1000-name list belongs
  with the catalogue entry in doc 15, not hardcoded in the frontend. *(Best first task —
  small, self-contained, visibly improves the app.)*
- **A fresh install cannot demonstrate comparison** — only one head per task ships as a
  default, so the user must train or import a second first.
- **N panes are equal-width columns**, so five heads gives five narrow strips. Left
  unsolved until real use shows how many simultaneous heads are useful.
- **Zoom is about the stage box, not the image content**, so zoom-at-cursor drifts slightly
  on a letterboxed image. Nothing misaligns (all panes and the overlay share the geometry);
  the gesture is just looser than it should be.
- **`GET /api/v1/annotate/image`** serves the viewer's image bytes from the *annotate* API
  slice. One implementation is right, the naming is not — promote it out of that slice if a
  third consumer appears.
- **`GET /api/v1/annotate/folder`** and `GET /api/v1/inference/source` both list a folder
  through `list_images`. Two endpoints over one helper is deliberate; a *third* consumer
  means migrating Wave 1's onto the newer shape and deleting it.

## State of the machine

- Installed: `dinov2-small`, `grounding-dino-tiny`, plus the three default heads (~6 MB).
  `dinov2-base` and `dinov2-large` are **not** installed, so any catalogue entry for them
  correctly reports "Download the backbone first".
- Waves 1 and 2 are merged to `dev`. `main` is untouched and must stay that way.
- A scratch segmenter was registered during feature 6's verification and **removed again** —
  the head registry is back to its original three.

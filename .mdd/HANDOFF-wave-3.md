# Wave 3 handoff — 1 of 6 features complete

**Branch:** `feat/dinotraining-wave-3` (pushed, 3 commits ahead of `dev`)
**Date:** 2026-08-18
**Next:** feature 2, `image-input-source`

## Resume in a new session with

```
/mdd plan-execute dinotraining-wave-3
```

Stale-job detection reads `.mdd/jobs/wave-dinotraining-wave-3/MANIFEST.md`, finds 1/6
`[x]`, and resumes at `image-input-source`. Choose **Resume**, not Discard.
Mode is **automated** (minimal interruptions, pause only on errors).

## If you are in a fresh cloud environment (claude.ai/code, a remote agent, a new machine)

The repo is ~2.6 MB and deliberately holds **no model weights and no venv** — both are
gitignored. Everything below must be created before any integration verification is
possible. On a local machine that already has them, skip this section.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest tests/ -q          # expect 616 passing
```

Then get real weights — ungated, Apache-2.0, ~174 MB total:

```bash
# with the backend running on 127.0.0.1:8756
curl -X POST http://127.0.0.1:8756/api/v1/models/dinov2-small/download   # 168 MB
# poll /api/v1/models/jobs/{job_id} until state=complete, then:
curl -X POST http://127.0.0.1:8756/api/v1/head-catalog/dinov2-linear-classifier-in1k.dinov2-small/install
curl -X POST http://127.0.0.1:8756/api/v1/head-catalog/dinov2-linear-segmenter-ade20k.dinov2-small/install
curl -X POST http://127.0.0.1:8756/api/v1/head-catalog/dinov2-linear-depth-nyu.dinov2-small/install
```

The head instance ids are generated per install, so they will **not** match the ones listed
below — read them back from `GET /api/v1/heads`. Expect CPU-only inference off a local
machine: correct, just slower.

**Confirm the bootstrap before building on it** by reproducing feature 1's verification —
the panorama case described under "Smoke test" further down. If the far-right region does
not differ from the background, something is wrong with the weights or the geometry, and
building feature 2 on top of that will waste the session.

## Wave planning decisions already made — do not re-litigate

- **Live webcam/video is deferred out of Wave 3.** Still images only. `video-stream-source`
  was replaced by `image-input-source`, which must establish an input contract a video
  source can later satisfy without the viewer changing. Proposed home is Wave 4 — to be
  confirmed when Wave 4 is planned, not decided here.
- **The Open Product Questions gate was waived deliberately.** The two unchecked items are
  scoped to Waves 5 and 6 (code-signing, first hyperscaler) and cannot affect an inference
  viewer. Recorded in both the wave doc and the initiative so it is not rediscovered.
- **Feature boundaries are settled:** the engine owns "features from an image",
  `multi-head-compose` owns "many heads from one set of features".

## What exists now

| # | Feature | Doc | State |
|---|---|---|---|
| 1 | inference-engine | [16](docs/16-inference-engine.md) | ✅ complete |
| 2 | image-input-source | — | ← **next** |
| 3 | multi-head-compose | — | planned |
| 4 | side-by-side-viewer | — | planned |
| 5 | inference-overlay-render | — | planned |
| 6 | same-task-head-compare | — | planned |

**Feature 1 delivers:** `POST /api/v1/inference` — one image path, one backbone, one head
instance → predictions **in original image coordinates**, tagged with the head's
`render_hint`. Verified end to end against real weights.

### What feature 1 changed in Wave 2 code

Three gaps where Wave 2 only ever needed the *training* direction:

1. **`app/ml/inference/geometry.py`** — new. `invert_boxes` / `invert_map` are the mirror
   of `transform_boxes` / `transform_mask` in `preprocess.py`. They live apart because the
   forward pair is a training concern and the inverse an inference one; each docstring
   points at the other. **If a third consumer of either direction appears, unify them.**
2. **`DECODERS` extended from 3 entries to 7.** It covered only trainable head types, so
   `decode_for` raised for all four non-trainable ones — including all three pretrained
   defaults. The four additions are `identity_decode`.
3. **`decode.py` moved `training/` → `heads/`.** Keyed by head-type id, imports only from
   `heads.*`, two consumers now. Its test moved to `tests/test_head_decode.py`.

## Feature 2 — what is already known

`image-input-source`: a single image or a folder. Two things doc 16 recorded specifically
so feature 2 does not rediscover them:

- **`detection_decode` decodes one image, not a batch** — it indexes `[0]` throughout
  (`app/ml/heads/decode.py`). Either loop per image, or generalise the decoder first.
  Do not assume a batched forward pass will work end to end.
- **`masks` and `depth-map` payloads are large.** A 900×300 map serialises as ~270k JSON
  numbers and measured ~460 ms per call. Fine for one image on loopback; watch it over a
  folder run. RLE or a PNG response is the obvious lever if it bites.

Reuse Wave 1's `app/ml/images.py` — `read_image` and `list_images` — rather than writing a
second file-reading path. `list_images` is deliberately **non-recursive** so pointing it at
`/` enumerates one level instead of walking the disk.

**The input contract is the real deliverable here**, not the file listing. Feature 4's
viewer and a future video source both consume it, so shape it as "something that yields
images one at a time with a stable identity", not as "a list of paths".

## Architecture that later features must honour

- **Two backbone passes, not one per task.** Cache key is `(backbone_id, geometry, size)`.
  Today's seven head types collapse to two passes: `aspect-preserve @ 448` (32×32 grid —
  detection, segmentation, depth) and `center-crop @ 224` (16×16 — classification).
  `consumes` is **not** part of the key: `cls` and `patches` come from the same
  `BackboneFeatures`, so a `cls` head shares a pass with a `patch-grid` one.
  What is impossible is *synthesising* one pass from another — CLS is attention over every
  patch in that pass, and a 14px patch at 448 covers half the extent it does at 224. This
  is feature 3's whole problem; the reasoning is in the wave doc's Open Research.
- **The renderer dispatches off `render_hint`**, never a task string it re-derives. Adding
  a head type to the registry later must render without touching feature 5's code.
- **Heads are presented via `HeadInstance.summary`** — never a filename. Wave 2 shipped one
  bug from breaking this, and doc 16 deliberately does *not* claim doc 12's `list_all`
  contract because the engine runs a head it is handed rather than offering a picker.
  Feature 6 is where that contract actually lands.

## Smoke test — free, no training required

Three real default heads are installed on this machine and need no training:

```
08ab54602f614a5f861cc64346ba1789   classification (IN1k, 1000 classes)
a81053b637a542d8923e38434120555d   segmentation   (ADE20k, 150 classes)
313c37d38a0844e2a39d61f94555e1be   depth          (NYUd, metres)
```

They exercise backbone → head → render across two dense render hints and both geometry
passes. The panorama used to verify feature 1 is worth recreating: a 900×300 image with an
object at x=770–880, i.e. exactly the region a centre crop destroys. Correct behaviour is
distinct segmentation/depth values in that region against the background — that is the
letterbox and the inversion both working.

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"image_path":"/abs/path.png","backbone_id":"dinov2-small","instance_id":"<id>"}' \
  http://127.0.0.1:8756/api/v1/inference
```

## Testing conventions established this wave

- **`StubBackbone` + patched `extract`** (`tests/test_inference_engine.py`). Loading
  `dinov2-small` in unit tests would make every one depend on a 168 MB download and seconds
  of model load. The doc-07 tensor contract is what the engine consumes and it is fully
  expressible in a stub — but **integration must still use real weights**, which is where
  every real bug this project has found came from.
- **`head_settings` fixture** in `tests/conftest.py` — a throwaway data + model root, so
  install tests never leak into the developer's real application-support directory.
- `tests/head_testkit.py` holds `install_fake_backbone` and the upstream state-dict builders.

## Gotchas

- **`git commit -m` with quotes in the message breaks under zsh**, and `git merge -F -`
  does not accept stdin at all. Write the message to a file and use `-F <file>`. Both bit
  this session.
- **Restart the dev server after backend edits** (`preview_stop` then `preview_start`);
  uvicorn does not reload. Stale Vite HMR errors persist in the browser console buffer
  across a restart and name files you never touched — verify with `tsc` + `read_page`, not
  the console.
- **`useState` seeded from async props is a live trap in this codebase** — it bit twice in
  Wave 2. Store the user's override and fall back to `props[0]`. Now in CLAUDE.md.
- **Do not use `perl -pi -e 's|…|…|'` with `|` as the delimiter** on regexes containing `|`.
- **The project has no prettier config** and uses single quotes. Do not run prettier.
- **A 300-line hook blocks writes.** `registry.py` is at 293 and `preprocess.py` at 259 —
  both are close, and the next addition to either will need a split rather than a trim.
- **MDD hashes** must be recomputed after any initiative/wave edit or the next
  `plan-execute` hard-stops:
  ```bash
  f=.mdd/waves/dinotraining-wave-3.md
  new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
  perl -pi -e "s/^hash: .*/hash: $new/" "$f"
  ```
  Feature docs carry no hash — only `initiatives/` and `waves/`.

## State to be aware of

- Locally downloaded: `dinov2-small`, `grounding-dino-tiny`, plus the three default heads
  above (~6 MB). `dinov2-base` and `dinov2-large` are **not** installed, so any catalogue
  entry for them correctly reports "Download the backbone first".
- Wave 2 is merged to `dev`; `main` is untouched and must stay that way.
- Jan normally merges to `dev` himself — he delegated the Wave 2 merge explicitly, which
  does not generalise. Ask.

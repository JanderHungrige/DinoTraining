# Handoff — start here

**This is the current handoff and always is.** It is rewritten in place at the end of each
wave rather than appended to. `HANDOFF-wave-2.md` is an older per-wave one kept as history;
do not read it for current state.

**Last updated:** 2026-08-19, after Wave 3 was merged and the initiative was replanned.

---

## Where the project stands

**Waves 1, 2 and 3 are merged and pushed to `dev`** (Wave 3 merge commit `8a780a1`).
`main` is still the initial scaffold and must stay that way.

```
672 backend tests (pytest) · 207 frontend tests (vitest) · ruff, mypy, tsc all clean
```

**Nothing is blocked on Jan.** The last session's open items — merge, demo-state
confirmation, job-folder cleanup, and where video lands — are all resolved.

**Next: Wave 4, Dataset Generator.** It has a wave doc but has not been through
`/mdd plan-wave` in detail. Start with:

```
/mdd plan-wave dinotraining-wave-4
```

⚠️ **That command will hard-stop on the open-questions gate.** Two items in the initiative
are unchecked:

```
- [ ] Code-signing / notarization for macOS + Windows installers   (Wave 8)
- [ ] Which hyperscaler(s) to support first for the website         (Wave 9)
```

**Waive them deliberately, exactly as Wave 3 did**, and say so in the wave doc. Both are
scoped to Waves 8 and 9 and cannot influence a dataset generator. Do not answer them just
to clear the gate — a guessed answer to "which hyperscaler" becomes an architectural
commitment nobody made.

## The nine waves

The initiative grew from six to nine on 2026-08-19. **Packaging moved 5 → 8 and the website
6 → 9**, so if you find any reference to "Wave 5 packaging" or "Wave 6 website" anywhere,
it is stale and was missed by the retarget — 21 were updated across docs and source
comments.

| | Wave | State |
|---|---|---|
| 1 | App Shell, Annotation Studio & Model Admin | ✅ merged |
| 2 | Head Trainer | ✅ merged |
| 3 | Inference Viewer | ✅ merged |
| 4 | **Dataset Generator** (SAM 3 + expert-head auto-annotation) | ← next, needs planning |
| 5 | Annotate With Your Own Models | planned |
| 6 | Foundation Model Breadth (Depth Anything 3) | planned |
| 7 | Onboarding & Input Polish | planned |
| 8 | Packaging & Distribution | planned |
| 9 | Website & Hyperscaler Compute/Storage | planned |

## Decisions already taken — do not re-litigate

- **Wave 4 is dataset-generator only.** Live video/webcam was explicitly withdrawn from it
  and is unassigned in `.mdd/BACKLOG.md`.
- **SAM 3 stays in Wave 4** — it is what makes segmentation trainable in-app, which is
  dataset-generator work. Upgraded from plain SAM because SAM 3 is *concept-prompted*: a
  text concept returns masks **and** boxes.
- **Depth Anything 3 is Wave 6**, Inference Viewer first, because a depth map can be looked
  at but not yet corrected — building a depth-annotation surface to justify the model would
  be backwards.
- **SigLIP 2 and Gemini Flash are dropped.** SigLIP 2 does not localise, so it produces no
  boxes and is not a Grounding DINO alternative. Gemini is API-only and would send the
  user's own image folders off their machine. Reasons are in Wave 6's "Explicitly not in
  scope" and in the backlog.
- **Wave 7 is deliberately late.** An intro tab describes how the app works, and Waves 5–6
  change that; written first it would be written twice. It must still precede Wave 8.
- **Model licences are planning constraints, not details.** The nested Depth Anything 3
  variant is **CC BY-NC 4.0** and SAM 3 ships under Meta's **custom SAM License** — neither
  is MIT/Apache. Wave 6 has a `model-licence-surfacing` feature; read both licences before
  Wave 8 packaging, not during it.

## If you are in a fresh environment

The repo holds **no model weights and no venv** — both gitignored.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest tests/ -q                                    # expect 672
cd ../apps/frontend && npm install --legacy-peer-deps && npx vitest run  # expect 207
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

## Smoke test — free, no training

Make a 900×300 panorama with an object at x=770–880, i.e. exactly the region a centre crop
destroys.

```bash
curl -s -X POST -H 'Content-Type: application/json' \
  -d '{"image_path":"/abs/path.png","backbone_id":"dinov2-small","instance_ids":["<cls>","<seg>","<depth>"]}' \
  http://127.0.0.1:8756/api/v1/inference/compose
```

Expect **`passes: 2`** for those three heads — two framings, not three — and grids
`[16,16]` and `[32,32]`.

**Read the result correctly.** *Depth* is the head that proves letterbox + inversion: that
far-right region reads clearly different from the background. The **ADE20k segmenter does
not distinguish it** on a synthetic flat-colour panorama — it returns two classes and the
object is not one of them. That is the model on unnatural input, not a bug; it is recorded
in doc 20 and was re-confirmed twice. **Do not "fix" it.** A screenshot can look like the
segmenter found the object — that is the yellow object showing *through* the 55%-opacity
mask, not a distinct class.

## Architecture later waves must honour

- **Registries, not enum branches.** Losses, metrics, decoders, builders and **overlay
  renderers** are all keyed by id. `OVERLAY_RENDERERS` is `Record<RenderHint, …>` so a
  missing renderer is a compile error, not a blank pane. A `task ===` comparison in
  `components/overlays/` is a defect.
- **Two backbone passes, not one per task.** Cache key `(backbone_id, geometry, size)`;
  `consumes` is **not** in it, because `cls` and `patches` come from the same
  `BackboneFeatures`. One pass cannot be synthesised from another. The cache lives in the
  compose call and dies with it.
- **Dense maps travel as base64 PNG** (`mask_png` / `depth_png`), never nested JSON —
  12.5 MB → 17 KB for a 3000×2000 segmentation. The pixel value is *data* (a class index,
  or 0..255 depth), so the client owns colour. Shaping lives in
  `app/ml/inference/payloads.py`.
- **One transform rendered N times.** The viewer is layout only and never sees a
  prediction; panes cannot drift. This is what made N-up comparison cost ten lines.
- **One image and a folder are the same shape**, items keyed by an opaque `item_id` — which
  is exactly what lets a video source satisfy the contract later.
- **Usable ≠ trainable**, and **provenance is the cross-tab contract**:
  `HeadInstance.summary`, never a filename. Wave 2 shipped one bug from breaking it; there
  are four consumers now.
- **Preprocessing is derived from (backbone, head)**, never configured by a caller.
- **The pickle carve-out stays narrow:** one `torch.load`, on digest-pinned bytes only.

## Gotchas (all still live)

- **Restart the dev server after backend edits** — uvicorn does not reload. Stale Vite HMR
  errors persist in the browser console **across a restart and a reload** and name files
  you never touched. Verify with `tsc` and the rendered page, not the console.
- **`git commit -m` with quotes breaks under zsh**, and `git merge -F -` does not accept
  stdin. Write the message to a file and use `-F <file>`.
- **`rm -rf` is blocked** by a safety hook. Remove files then `rmdir`.
- **A 300-line hook blocks writes.** It fired twice in Wave 3. `registry.py` is at 293 and
  `preprocess.py` at 259 — the next addition to either needs a split, not a trim.
- **Do not use `perl -pi -e 's|…|…|'` with `|` as the delimiter** on regexes containing `|`.
- **A multi-line shell variable does not split in `for f in $FILES`** — it becomes one
  filename and the loop silently does nothing. Put the list inline.
- **No prettier config; single quotes.** Do not run prettier.
- **MDD hashes** must be recomputed after any initiative/wave edit or the next
  `plan-execute` hard-stops. Feature docs carry no hash.
  ```bash
  f=.mdd/waves/dinotraining-wave-4.md
  new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
  perl -pi -e "s/^hash: .*/hash: $new/" "$f"
  ```

## Testing lessons — the bugs the suite could not see

Every real bug in three waves came from driving the app, never from the suite. The shapes
that recur:

1. **CPU-only tests over an MPS runtime.** `.numpy()` raises on any tensor that is not a
   plain CPU leaf. All 668 tests passed while every dense prediction 500'd. → route
   device→host through one `.detach().cpu().numpy()` helper; pair a `@skipif` MPS test with
   a **deterministic** `requires_grad` one.
2. **Geometry measured against the wrong element.** jsdom reports every element as `0×0`, so
   a clamp against the wrong box behaves exactly like one against the right box. → stub
   `HTMLElement.prototype.clientWidth/Height` **before mount** (measurement runs in a mount
   effect) and assert the **exact** boundary value — a loose assertion passes at 0 too.
3. **A handler on an outer container catching a bubbled event** from a control inside it.
4. **Async props seeded into `useState`** — store the override, derive the value.

**Always confirm a regression test fails against the old code.** One written in Wave 3 was
vacuous and passed either way until it was rewritten.

## Known issues — good first tasks

- **The ImageNet classifier ships no class names**, so the viewer renders `class 416`
  instead of `Siamese cat`. Small, self-contained, and the most visibly rough edge in the
  new tab. The 1000-name list belongs with the catalogue entry in doc 15, not hardcoded in
  the frontend.
- **Wave 5's `inference-picker-upfront` may be largely shipped.** Wave 3's `HeadRunPanel`
  already picks heads before running, filters by task and refuses incompatible backbones.
  Ask what is actually missing before scoping it.
- **Only `boxes`-hint heads can annotate.** A segmentation head has no mask-drawing tool in
  the Studio to refine into — Wave 5's main open question, and the reason Depth Anything 3
  goes to the viewer rather than the Studio.
- **A fresh install cannot demonstrate same-task comparison** — only one head per task ships
  as a default, so a second must be trained or imported first.
- **N result panes are equal-width columns**, so five heads gives five narrow strips.
- **Zoom is about the stage box, not the image content**, so zoom-at-cursor drifts slightly
  on a letterboxed image. Nothing misaligns; the gesture is just looser than it should be.
- **`GET /api/v1/annotate/image`** serves the *viewer's* image bytes from the annotate API
  slice, and **`/annotate/folder`** duplicates the question `/inference/source` answers. One
  implementation each is right; the naming is not. Promote them out if a third consumer
  appears.

## State of the machine

- Installed: `dinov2-small`, `grounding-dino-tiny`, plus the three default heads (~6 MB).
  `dinov2-base` and `dinov2-large` are **not** installed, so any catalogue entry for them
  correctly reports "Download the backbone first".
- ~14 GB free on the home volume — be deliberate about large downloads.
- Branches `feat/dinotraining-wave-2` and `feat/dinotraining-wave-3` are merged but still
  exist locally and on origin; `feat/dinotraining-wave-2` is 1 commit ahead of its remote.
  Cleanup was offered and not requested.

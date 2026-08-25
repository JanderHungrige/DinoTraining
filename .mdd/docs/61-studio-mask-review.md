---
id: 61-studio-mask-review
title: Masks in the Studio — Review the Segmentation, Not Its Shadow
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [45-concept-segmentation-everywhere, 47-box-review-list, 22-mask-dataset-store, 28-mask-review-ui]
relates: [05-annotation-canvas, 42-foundation-boxes-everywhere, 60-box-class-picker, 27-grounded-sam-annotator]
source_files:
  - backend/app/ml/annotators/foundation.py
  - backend/app/api/v1/generate_foundation.py
  - backend/app/api/v1/datasets.py
  - backend/app/datasets/masks.py
  - apps/frontend/src/types/annotation.ts
  - apps/frontend/src/api/foundation.ts
  - apps/frontend/src/api/datasets.ts
  - apps/frontend/src/lib/saveAnnotations.ts
  - apps/frontend/src/components/MaskLayer.tsx
  - apps/frontend/src/lib/decodeMap.ts
  - backend/app/ml/inference/payloads.py
  - backend/app/ml/foundation/concept.py
  - apps/frontend/src/components/overlays/MapOverlay.tsx
  - apps/frontend/src/components/AnnotationCanvas.tsx
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/hooks/useSessionImages.ts
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/datasets/{dataset_id}/images/masks
models:
  - masks
test_files:
  - backend/tests/test_foundation_masks.py
  - backend/tests/test_dataset_image_masks_api.py
  - apps/frontend/src/components/MaskLayer.test.tsx
  - apps/frontend/src/lib/saveAnnotations.test.ts
  - apps/frontend/src/hooks/useAnnotationSession.masks.test.ts
data_flow: .mdd/audits/flow-studio-mask-review-2026-08-25.md
last_synced: 2026-08-25
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, segmentation, grounded-sam, sam3, coco-rle, mask-review, dataset-store]
path: Annotation Studio/Review
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 61 — Masks in the Studio

## Purpose

When the Studio runs a concept segmenter, show the **segmentation** it produced, and store
it. Today the Studio shows the bounding boxes and throws the masks away.

## The report

> "Using SAM, the result in annotation are (correct) bounding boxes, while it should be a
> segmentation mask, correct? As the bounding boxes are also correct, maybe add the
> segmentation mask as default with an option to show the bounding boxes."

Correct on all three counts. The boxes are right *because* they are the mask's extents —
`ml/annotators/foundation.py:_from_concept` runs the full pipeline, keeps `proposal.box`,
and drops `proposal.counts` on the floor. Every Studio run pays for a segmentation and
discards it.

## Reversing a decision, on the record

Doc 45 says plainly:

> "Wave 5 declined mask review in the Studio — its promise is hand-refinement and there is
> no mask editor — and that decision stands. Nothing here reverses it."

**This reverses it,** and the reasoning that made it right no longer holds. That decision
answered "should the Studio let you *edit* masks?", and the answer is still no — there is
no mask editor here and this feature does not add one. What it answers instead is "should
the Studio *show and keep* the mask it already computed?", which was never really the same
question. Boxes stay fully editable; masks are shown, verdicted and stored as they came.

## What is stored, and why not both

**One annotation per object.** A mask-carrying object is stored as a `masks` row; a
hand-drawn or detector-only box is stored as a `boxes` row. Never both for one object.

This is not a size optimisation. `build_coco` walks the two tables independently and emits
each as its own annotation, and a stored mask already exports with `segmentation`, `bbox`
— derived by `rle_bbox` at `coco.py:75` — and `area`. Writing a `boxes` row as well would
put **two** annotations on one object in every export, one bbox-only and one segmentation,
and silently double every segmented object in anything trained from that file.

So "masks plus derived boxes" means exactly that: the RLE is stored, and the box is
derived — by the exporter, and in the UI from the `x/y/w/h` that `MaskStore._row` already
computes on write.

## Architecture

```
propose   ConceptSegmenter.propose ──> MaskProposal(counts, size, box, score, concept)
                                          │
              ml/annotators/foundation.py │  keeps BOTH halves now
                                          v
          POST /generate/foundation ──> boxes[] each with optional mask{rle, png}
                                          │
review    CanvasBox.mask ────────────────>│ MaskLayer paints it, tinted by verdict
                                          │ the box button stays the hit target
                                          v
save      PUT /images/masks   mask-carrying annotations (rle)
          PUT /images         box-only annotations
                                          │
reload    GET /images/masks?path=… ──────>┘ per image, on demand
```

The RLE travels **on the annotation**, not paired to a proposal by index. Doc 28's
`saveImageMasks` pairs by index and refuses a length mismatch, which is correct for the
Dataset Generator — an immutable proposal, verdicts only. The Studio's list is edited:
boxes are drawn, removed, and discarded wholesale by the threshold slider. Any of those
breaks index pairing, and a broken pairing is a **silent** mislabel — the save succeeds and
every mask after the edit carries the wrong verdict and class.

## Data Model

No schema change. `masks` already holds everything: RLE, derived bbox, label, prompt,
score, producer. This feature writes to a table Wave 4 built and never wired to the Studio.

## API Endpoints

### `GET /api/v1/datasets/{dataset_id}/images/masks?path=<stored path>`

One image's stored masks, with the preview PNG.

**Per image, not in the dataset listing**, and the reason is size: `GET
/datasets/{id}/images` ships every image's boxes inline, which is right for four floats
each. An RLE is a run list over the whole frame — roughly 15 KB as JSON for a 2464x1600
mask — and the OSDaR23 rail dataset is 392 images. The Studio shows one image at a time,
so one image's worth is what it asks for.

```json
{ "path": "...", "width": 2464, "height": 1600,
  "masks": [ { "label": "positive", "provenance": "grounded-sam",
               "rle": { "size": [1600, 2464], "counts": [...] },
               "x": 0, "y": 0, "w": 100, "h": 80,
               "score": 0.82, "prompt": "sky", "producer": {...},
               "mask_png": "iVBOR..." } ] }
```

* `404` — unknown dataset. An unknown *path* is an empty list, not a 404: an image with no
  masks and an image not in the dataset are the same thing to a review surface opening on
  it, and 404 would make the common case look like an error.

### `POST /api/v1/generate/foundation` (extended)

Each box gains `mask: { rle, png } | null`. Null for a detector — RF-DETR has no
segmentation — and populated for a concept segmenter.

Extending this rather than pointing the Studio at `/generate/masks` keeps **one** proposal
call and one response shape. `/generate/masks` is keyed by `annotator_id`, which the
Studio does not have (it holds a `foundation_id`), so using it would mean exposing the
annotator mapping to the client for no gain.

## Business Rules

1. **Masks are shown by default; boxes are a toggle.** The mask is the finer answer and the
   box is derivable from it. `Show bounding boxes` draws the rects on top; it does not hide
   the masks, because the two together are how you check that a box is tight.
2. **The toggle only appears when something has a mask.** A control that does nothing reads
   as broken — the same rule doc 47 applied to the threshold slider.
3. **The mask's box stays the hit target.** Mask pixels are awkward to click and impossible
   to focus; the derived rect gives a real focusable button, so keyboard operation, the
   1/2/3 verdict keys and the accessibility tree work exactly as they do for a box. This is
   doc 28's rule, reused rather than re-decided.
4. **A mask is tinted by its verdict**, using the same three colours the box borders use, so
   one legend serves both surfaces.
5. **A mask cannot be reshaped, and a box drawn by hand never gains one.** There is no mask
   editor and this does not add one. Dragging on the image produces a box, as it always did.
6. **Re-running a proposal keeps hand-drawn boxes and replaces everything else** — the
   existing rule, unchanged. Hand-drawn boxes are work the model cannot reproduce; a
   previous run's masks are not.
7. **Both sets are written on every save, including empty ones.** An image whose masks were
   all rejected must have its mask set cleared, not left behind — and `replace_image_masks`
   replaces, so an empty list is how "none any more" is said. This is also why reload is
   mandatory rather than a nicety: a Studio that did not load an image's masks would wipe
   them on the next save.
8. **Masks are written before boxes.** The two PUTs are not atomic (see Known Issues). If
   the second fails, the failure is reported and the counters come from the backend, so the
   UI shows what was actually stored rather than what was attempted.
9. **A mask annotation is never also a box annotation.** See "What is stored" above.

## Data Flow

Full trace in `.mdd/audits/flow-studio-mask-review-2026-08-25.md`. What changes:

```
before   MaskProposal → box only         → boxes table
after    MaskProposal → box + rle + png  → masks table (box derived on write and on export)
```

Unchanged: how a class is carried (`concept` → `prompt`), the verdict vocabulary, the
counters — `DatasetStore.counts` already sums boxes and masks per verdict, because doc 22
built it that way.

## Dependencies

* `45-concept-segmentation-everywhere` — the pipeline whose masks were being discarded, and
  the doc whose decision this reverses.
* `22-mask-dataset-store` — the `masks` table, the RLE codec, `replace_image_masks`.
* `28-mask-review-ui` — the hit-target rule and the verdict colours, reused.
* `47-box-review-list` — the row each mask gets, unchanged.

## Security

No new input surface of consequence. The new route takes a dataset id (a key into a closed
set, resolved through `DatasetStore`) and a stored path used only in a parameterised
`WHERE`, never to open a file — the image bytes still come from the existing
`/annotate/image` route with its allowlist in front.

RLE arriving from a client is validated by `MaskRle`'s existing model validator, which
checks that the runs cover exactly `height × width`; a malformed one is a 422 through the
route's existing `ValueError` backstop, not a crash in numpy.

## Verified

**In the running app on 2026-08-25**, Grounded SAM for `sky` over an OSDaR23 rail frame:

* the Studio drew the **segmentation** — the tree-line silhouette — with no rectangle;
* `Show bounding boxes` drew the box on top of it, visibly looser than the mask, which is
  the comparison rule 1 exists for;
* Save wrote **one** row: `masks` 1, `boxes` 0 for that image in that dataset. The RLE is
  13,691 characters, which is the ~15 KB that made per-image loading the right call;
* a full page reload, reopening the dataset with the **prompt** proposer rather than SAM,
  brought the mask back with its class and a clean (non-dirty) session — so the reload path
  does not depend on what proposed it;
* the COCO export carries **one** annotation for the object:

```
keys: area, bbox, category_id, id, image_id, iscrowd, score, segmentation
bbox: [698.0, 0.0, 1082.0, 820.0]     <- derived from the RLE
area: 289705                          <- the mask's area, not the box's 887240
segmentation: 2801 runs
```

That last line is the whole justification for the storage rule, measured: the derived box
is there, the area is the segmentation's, and there is no second annotation.

## Corrections

**2026-08-25 — the fizzle, and one canvas instead of thirty.**

Reported as "the box and segments seem to be found correctly, but there is still an overall
fizzle when shown... looks like a displaying error", with a screenshot of a fine green
speckle over the entire frame — sky, trees, everything the mask is not — and the real mask
solid underneath it. Reported from the packaged app, not a dev browser.

**The data was never wrong.** Decoding the stored mask in Chromium gives exactly two
distinct byte values, 0 and 255, with 289,705 foreground pixels — the same number the COCO
export reports as the area. So the RLE, the PNG encode and the store were all correct and
the fault was in reading the PNG back.

`new Image()` → `drawImage` → `getImageData` runs the image through **colour management**.
The browser converts from the image's colour space to the canvas's, and where the
conversion cannot land on an exact integer it *dithers*. Dithering a photograph is
invisible; dithering data is not. A background of 0 comes back as a scatter of 0s and 1s,
and `value > 0` — which is what both overlays tested — promotes every one of those 1s to a
fully painted pixel. Chromium does not dither these; WebKit does, which is why it appears
in the packaged app and not in a dev browser, and why the Inference Viewer showed it worst:
that payload's classes are literally 0 and 1, so a one-level error *is* a different class.

Three defences, in `lib/decodeMap.ts` and its callers:

1. `createImageBitmap(blob, { colorSpaceConversion: 'none' })` — the standard way to say
   "these are bytes, do not convert them", with an `<img>` fallback for older WebKit that
   rejects the options bag;
2. an `{ colorSpace: 'srgb' }` context with `imageSmoothingEnabled = false`, so nothing
   downstream resamples or re-converts;
3. **threshold instead of testing for non-zero.** Masks are encoded 0/255, so `>= 128` is
   correct whatever any browser does to the low bits. This is the defence that does not
   depend on a browser honouring a flag.

**And one canvas for every mask, not one each.** The first implementation stacked an
absolutely-positioned full-resolution canvas per annotation. At 2464x1600 that is 15.8 MB
of pixel buffer apiece: thirty chess pieces would have asked the compositor for roughly
half a gigabyte, and thirty translucent layers darken each other wherever masks overlap.
They are composited into a single buffer now, which is cheaper *and* truer — where two
masks meet the later one wins outright, the same last-writer-wins the backend's own index
map produces.

Verified after: one canvas, 289,705 painted pixels, 3,652,695 fully clear, and **zero**
stray alpha values.

**Round two: the flag is not honoured, so the encoding changed instead.**

The two surfaces were given deliberately different defences, which made the next report
diagnostic: the Studio came back clean and the Inference Viewer did not. The Studio is the
one protected by the threshold; the Viewer is the one that depended on
`colorSpaceConversion: 'none'`. So WebKit converts the image whatever it is asked, and no
client-side flag can prevent it.

Which leaves the encoding. The Viewer's payload is a **composited class map**, and with a
single phrase its classes are 0 and 1 — adjacent bytes, where one level of dither *is* the
other class. `encode_class_map` now spreads the indices as far apart as the range allows
and sends the multiplier as `class_stride`:

| classes | stride | pixel values |
|---|---|---|
| background + 1 phrase | 255 | 0, 255 |
| background + 3 phrases | 85 | 0, 85, 170, 255 |
| ADE20k's 150 | 1 | 0…149, exactly as before |

The client divides and rounds, so it now takes a **128-level** error to confuse background
with an object rather than one. ADE20k degrades to the old encoding and needs nothing:
its class 0 is `wall`, a real class that is painted anyway, so a dithered pixel there is a
slightly wrong colour rather than a hole in the background.

Verified on the wire after: `class_stride: 255`, `present_classes: [0, 1]`, and the PNG's
distinct pixel values are `0` and `255` where they used to be `0` and `1`. The rendered
overlay is 562,073 painted pixels, 3,380,327 fully clear, and exactly **one** distinct
colour.

## Known Issues

- "**The two writes are not atomic.** There is no endpoint that takes boxes and masks
  together, so a save is `PUT /images/masks` followed by `PUT /images`. Masks go first so
  the likelier failure leaves the image entirely unchanged, and the counters come from the
  backend so the UI never claims more than was stored — but a box write failing after a
  successful mask write leaves new masks beside old boxes."
- "**A mask cannot be reshaped.** There is still no mask editor, which is the part of doc
  45's decision that stands. A mask you disagree with can be rejected or removed, not
  corrected."
- "**A hand-drawn box never gains a mask.** Drawing on the image produces a rectangle, as
  it always did; there is no 'segment this box' action, though SAM is exactly the model
  that could answer one."
- "**Masks are not thresholded separately.** The score slider filters masks and boxes
  together on the one list, which is right for a mixed image and possibly too blunt for a
  run that produced only masks."
- "**A re-run discards loaded masks.** `propose` keeps hand-drawn boxes and replaces
  everything else, and a mask loaded from the store is 'everything else'. That is the
  existing rule applied consistently, but it means re-running SAM on an image you already
  segmented loses the earlier verdicts."
- "**WebKit colour-manages canvas image data whatever it is asked.** `colorSpaceConversion:
  'none'` did not stop it — confirmed by the Studio (threshold-protected) coming back clean
  while the Viewer (flag-dependent) did not. Anything that puts *data* through
  `drawImage`/`getImageData` must assume the low bits are unreliable and encode
  accordingly; see `encode_class_map`."
- "**A map with more than ~127 classes cannot be spread.** The stride falls to 1 and such a
  payload is exactly as fragile as before. No head shipped today is affected — ADE20k's
  class 0 is a real class — but a future segmenter with many classes *and* a true
  background would be."
- "**The Dataset Generator is untouched.** It keeps its own mask review and its own
  index-paired save, which remain correct for a surface where the proposal is immutable." 

## Bugs

(none yet — populated by /mdd bug when issues are reported)

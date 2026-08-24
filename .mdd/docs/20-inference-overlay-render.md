---
id: 20-inference-overlay-render
title: Inference Overlay Render — Dispatch on render_hint, and a PNG Transport
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-3
wave_status: complete
depends_on: [18-multi-head-compose, 19-side-by-side-viewer]
relates: [05-annotation-canvas, 08-head-registry, 16-inference-engine, 21-same-task-head-compare]
source_files:
  - backend/app/ml/inference/payloads.py
  - backend/app/ml/inference/engine.py
  - apps/frontend/src/api/inference.ts
  - apps/frontend/src/lib/overlayPalette.ts
  - apps/frontend/src/components/overlays/registry.tsx
  - apps/frontend/src/components/overlays/BoxOverlay.tsx
  - apps/frontend/src/components/overlays/LabelOverlay.tsx
  - apps/frontend/src/components/overlays/MapOverlay.tsx
  - apps/frontend/src/components/HeadRunPanel.tsx
  - apps/frontend/src/hooks/useHeadRun.ts
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - backend/tests/test_inference_payloads.py
  - apps/frontend/src/components/overlays/registry.test.tsx
  - apps/frontend/src/lib/overlayPalette.test.ts
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [overlay, render-hint, registry, png-transport, segmentation, depth, palette]
path: Inference/Overlay
integration_contracts:
  - function: OVERLAY_RENDERERS[render_hint]
    when: a head type is added to the backend registry
    why: adding a renderer here must be the only UI change; a task string in a condition
      anywhere in the overlays folder has broken it
satisfies_contracts:
  - from: 19-side-by-side-viewer
    function: SideBySideViewer renderOverlay(rendered)
    when: drawing predictions over the result pane
    status: done
    verified_at: "apps/frontend/src/tabs/InferenceViewerTab.tsx:76"
  - from: 18-multi-head-compose
    function: run_heads via POST /api/v1/inference/compose
    when: running the selected heads over the current image
    status: done
    verified_at: "apps/frontend/src/hooks/useHeadRun.ts:104"
security_read_sites: []
known_issues:
  - "The pretrained ImageNet classifier ships **no class names**, so its results render as `class 416` rather than `Siamese cat`. The fallback is working as designed (doc 16 requires the viewer render *something* rather than throw), but the head is close to unreadable in the UI. The 1000-name list belongs with the catalogue entry in doc 15, not hardcoded in the frontend."
  - "All selected predictions are layered into the one result pane, so two masks stack and the lower one is invisible. `21-same-task-head-compare` is where N-up panes land; until then, running two dense heads at once is not useful."
  - "Depth is transported as 8-bit normalised, which is a *display* encoding. `min`/`max` make it invertible to roughly 1% of the scene range — fine for a colour ramp, not for anything metric. A consumer needing true depth should take it from the tensor."
sister_projects: []
---

# 20 — Inference Overlay Render

## Purpose

Draw what a head predicted, **dispatching off the head type's `render_hint`** — `labels`,
`boxes`, `masks` or `depth-map` — and never off a task string the renderer re-derives.

It is also where the dense-payload problem doc 18 measured gets fixed, because that is
what made the maps drawable at all.

## Architecture

```
prediction.render_hint ──> OVERLAY_RENDERERS[hint]      Record<RenderHint, Renderer>
                              │
        ┌─────────────────────┼──────────────────┬────────────────┐
        ▼                     ▼                  ▼                ▼
   LabelOverlay          BoxOverlay         MapOverlay       MapOverlay
   (panel, no            (DOM boxes via     (canvas,         (canvas,
    geometry)             toDisplay)         classColour)     depthColour)
```

`Record<RenderHint, …>` rather than a lookup with a default: adding a hint to the union
without adding a renderer becomes a **compile error** rather than a silently blank pane.

## The transport change — measured, not assumed

Doc 18 recorded that the composed response was 5.5 MB and that "RLE or a PNG response is
the obvious lever". Measuring first showed it was worse than recorded:

| Case | Nested JSON lists | base64 PNG | Ratio |
|---|---|---|---|
| 3000×2000 segmentation | 12,521,000 B | 17,493 B | **716×** |
| the mask array alone | 18,520,656 B | 17,144 B | 1080× |
| 3 heads composed, 900×300 | 5,499,922 B | 73,909 B | 74× |

The numbers were almost all redundant. A mask is upsampled from a **32×32 patch grid**, so
six million JSON integers were encoding a few thousand values of real signal, and PNG's
run-length filtering removes exactly that redundancy. Drawing a PNG is also *less* frontend
work than building `ImageData` from nested arrays — the browser does the decompression.

**The pixel value is data, not colour.** A mask PNG carries the class index; a depth PNG
carries 0..255 normalised across `min`..`max`. No palette is baked in, so the client owns
presentation, which is what keeps this feature — rather than the backend — responsible for
how things look.

## Data Model

### Payload per render hint

| Hint | Payload |
|---|---|
| `labels` | `scores: number[]` over `class_names` |
| `boxes` | `boxes: [x,y,w,h][]` in source pixels, `scores`, `classes` |
| `masks` | `mask_png` (base64), `present_classes`, `height`, `width` |
| `depth-map` | `depth_png` (base64), `min`, `max`, `height`, `width` |

### The palette is generated, not listed

ADE20k alone is 150 classes; a hand-written table would need extending every time a head
with a different class count is imported. `classColour(index)` walks the hue circle by the
golden angle (137.508°) so successive indices land far apart — adjacent class ids are what
adjacent regions of a segmentation usually are, and near-identical colours for them would
hide the boundary. Alternating lightness adds a second axis once hues start to repeat.

Depth uses a **monotonically lightening** ramp, deliberately not a rainbow: a hue that
cycles makes the eye read a boundary where the data has none.

## Business Rules

- **Dispatch on `render_hint`, never on `task`.** Two head types can share a task and a
  renderer. A `task ===` comparison anywhere in `components/overlays/` is a defect.
- **Boxes are converted through `toDisplay` only.** They arrive in source pixels because
  doc 16 inverts the geometry server-side; `lib/geometry.ts` owns source→displayed, and its
  own docstring explains that a second conversion site is how marks end up subtly offset
  with nobody able to tell which is wrong. `toDisplay` already folds in the letterbox
  offset — adding `offsetX` again is the classic double-offset bug.
- **Boxes, scores and classes are read positionally.** The backend drops from all three
  arrays together precisely so index N means the same detection in each.
- **A missing payload renders nothing, not an exception.** A head that returned an empty
  result must not take the pane down with it.
- **Maps are `image-rendering: pixelated`.** The map is data upsampled from a coarse grid;
  smoothing it invents boundaries the model did not predict.
- **The backbone is derived from the head selection**, not chosen separately. A head only
  runs against the backbone it was registered for, so a separate control would let the user
  build an invalid combination and learn about it from a 409. The first selected head fixes
  the backbone and the rest are disabled with an explanation while it stands.
- **Heads are offered by `summary`** — task, provenance, training data — never a filename.
  Doc 12's cross-tab contract, which Wave 2 already broke once.
- **A stale result is cleared when the selection changes**, and an in-flight run is aborted
  when another starts. Otherwise the slower response wins and shows the wrong image's result.

## Data Flow

Greenfield on the frontend. On the backend this feature **changes doc 16's payload shape**:
`mask` and `depth` nested lists are replaced by `mask_png` and `depth_png`. The only
consumers were doc 16's own tests, which now assert the decoded map.

`_build_payload` and its four helpers moved from `engine.py` to a new
`app/ml/inference/payloads.py` — doc 18 recorded that the next change to payload shaping
should split that file rather than push it past the 300-line gate. `engine.py` went from
262 to 160 lines.

## Dependencies

`18-multi-head-compose` for the predictions, `19-side-by-side-viewer` for the pane and the
`RenderedImage` geometry, `lib/geometry.ts` (doc 05) for the box conversion.

## Security

No new input surface. The one new consideration is that the client now decodes a
**server-supplied PNG** into a canvas. It comes from the app's own loopback backend, is
drawn to a canvas rather than injected into the DOM, and is never used as a URL or a path —
so a malformed one produces a blank overlay, not code execution. `MAX_PNG_CLASSES` guards
the other direction: a class index that would not fit in a byte raises rather than silently
wrapping class 300 round to class 44.

## A bug the whole suite could not see

`.numpy()` raises on any tensor that is not a plain CPU leaf. The backbone runs on **MPS**
on this machine, so the decoded map is an MPS tensor and every dense prediction 500'd —
while all 668 backend tests passed, because every one of them builds its tensors on the
CPU. The previous transport used `.tolist()`, which quietly accepts MPS tensors, so the
bug only became reachable when the maps moved to PNG.

Fixed by routing every conversion through one `to_numpy()` that does
`.detach().cpu().numpy()`. Two regression tests: an MPS one that skips off Apple silicon,
and a `requires_grad` one that is deterministic everywhere and fails in exactly the same
place for the same reason. Both confirmed to fail against the pre-fix code.

## Verified

In the running app, on the 900×300 panorama with the three default heads:

```
classifier + segmenter   2 backbone passes · 445 ms   (labels panel + mask canvas)
depth alone              1 backbone pass  · 225 ms
mask canvas              900x300 backing store, drawn into a 338px pane
class 0 → rgb(218,62,62)   class 6 → rgb(101,218,62)   — distinct, at the right pixels
depth                    145 distinct colours across the ramp
```

**On the smoke test, honestly:** the handoff asks for distinct values in the far-right
region (x=770–880) that a centre crop destroys. **Depth shows this clearly** — that region
reads "far" against a "near" background, so letterbox and inversion are both working. The
**segmenter does not**: it labels that region the same class as the background. That is the
model on a synthetic flat-colour image, not a rendering fault — confirmed by reading the
raw mask, which genuinely holds one class across that row. The renderer was proven
separately by sampling two pixels the mask *does* distinguish and confirming they render as
different colours.

## Known Issues

- **The pretrained ImageNet classifier ships no class names**, so its results read as
  `class 416` instead of `Siamese cat`. The fallback behaves as doc 16 requires — render
  something rather than throw — but the head is close to unreadable. The 1000-name list
  belongs with the catalogue entry in doc 15, not hardcoded in the frontend.
- **All predictions layer into one result pane**, so two masks stack and the lower one is
  invisible. `21-same-task-head-compare` is where N-up panes land.
- **Depth's 8-bit encoding is for display.** `min`/`max` make it invertible to about 1% of
  the scene range; anything metric should read the tensor.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

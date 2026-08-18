---
id: 19-side-by-side-viewer
title: Side-by-Side Viewer — Original vs Result, One Transform
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-3
wave_status: complete
depends_on: [17-image-input-source]
relates: [05-annotation-canvas, 20-inference-overlay-render, 21-same-task-head-compare]
source_files:
  - apps/frontend/src/lib/viewTransform.ts
  - apps/frontend/src/hooks/useViewTransform.ts
  - apps/frontend/src/components/SideBySideViewer.tsx
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/lib/viewTransform.test.ts
  - apps/frontend/src/components/SideBySideViewer.test.tsx
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [viewer, zoom-pan, layout, accessibility, react, render-prop]
path: Inference/Viewer
integration_contracts:
  - function: SideBySideViewer renderOverlay(rendered: RenderedImage)
    when: drawing anything on top of the result pane
    why: the overlay must be positioned from the image's *rendered* geometry, not the
      container's, or every mark is offset on a letterboxed image
satisfies_contracts:
  - from: 17-image-input-source
    function: useImageSource(path) → current item
    when: the viewer shows the selected image
    status: done
    verified_at: "apps/frontend/src/tabs/InferenceViewerTab.tsx:18"
security_read_sites: []
known_issues:
  - "Zoom is about the stage box, not the image content inside it. With `object-fit: contain` on a letterboxed image the two differ, so zooming in on a 900x300 image inside a 4:3 frame drifts slightly from the pixel under the cursor. Both panes drift identically and the overlay uses the same `fitContain` geometry, so nothing misaligns — but the gesture is looser than it should be. Fixing it means sizing the stage to the rendered image rather than the frame."
  - "`aspect-ratio: 4 / 3` on the frame is a fixed guess. A very wide or very tall image wastes a lot of pane. Sizing the frame from the image's own aspect ratio needs the natural size before first paint, which is why it was not done here."
sister_projects: []
---

# 19 — Side-by-Side Viewer

## Purpose

Show the user's image and the annotated result **next to each other**, with zoom and pan
that move both panes together. Comparing a mask against the pixels underneath it is the
entire reason this wave exists, and that comparison is worthless if the two panes drift
apart by a few pixels.

**This feature is layout only. It does not know what a head produces.** It has no
knowledge of boxes, masks, depth or labels — feature 20 draws those through a render prop.
If a `render_hint` string appears anywhere in this feature's source, the boundary has been
broken.

## Architecture

```
                     useViewTransform
                            │
                  { scale, tx, ty } ── one state
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
      ┌───────────────┐          ┌───────────────┐
      │   Original    │          │    Result     │
      │   <img>       │          │   <img>       │
      │               │          │  + overlay    │  ← renderOverlay(rendered)
      └───────────────┘          └───────────────┘
         same transform applied to both
```

### Synchronisation by construction, not by mirroring

The obvious implementation is two panes that each own a transform and notify each other on
change. That is the wrong shape: mirrored state produces feedback loops (pane A's update
triggers pane B's, which triggers A's), needs an "is this echo mine?" guard, and drifts by
a rounding error per event until the panes visibly disagree.

Here there is **one transform object rendered twice**. The panes cannot disagree, because
there is nothing to disagree about. No effects, no echo guard, no drift.

## Data Model

### `ViewTransform` (plain object, in `lib/viewTransform.ts`)

| Field | Type | Notes |
|---|---|---|
| `scale` | `number` | 1 = fit. Clamped to `[MIN_SCALE, MAX_SCALE]` = `[1, 8]`. |
| `tx`, `ty` | `number` | Container-pixel translation, applied before scale. |

The maths lives in pure functions, separate from the hook, because the interesting cases —
zoom-at-cursor, clamping — are arithmetic and deserve tests that no React renderer sits in
front of.

- `zoomAt(transform, focusX, focusY, factor, size)` — zoom about a point, so the pixel
  under the cursor stays under the cursor. Zooming about the centre instead is the thing
  that makes a viewer feel broken: the user points at a detail and it slides away.
- `panBy(transform, dx, dy, size)` — translate, then clamp.
- `clampTransform(transform, size)` — the invariant below.

### The clamping invariant

**The scaled content always covers the container.** With container width `W` and scale `s`,
content width is `W·s`, so `tx ∈ [W(1−s), 0]`. At `s = 1` that collapses to `tx = 0` —
panning is impossible when the image already fits, which is correct rather than a special
case.

Without this the user can drag the image off-screen and be left staring at an empty pane
with no obvious way back, which is the single most common way a hand-rolled pan control
fails.

## API Endpoints

None. This feature is frontend layout.

## Business Rules

- **Both panes always show the same image.** The right pane is the same source pixels plus
  whatever the overlay draws. It is not a separate render of a different thing.
- **The overlay receives `RenderedImage`, not the container box.** An `object-fit: contain`
  image is letterboxed when the aspect ratios differ, so the container is not the image.
  `fitContain` from `05-annotation-canvas`'s `lib/geometry.ts` is reused rather than a
  second implementation — that module's docstring already says a second conversion site is
  how marks end up subtly offset with nobody able to tell which is wrong.
- **Zoom is about the pointer**, pan is clamped, and double-click resets.
- **Everything is reachable from the keyboard**: `+`/`-` zoom, arrows pan, `0` resets, and
  the same actions exist as real buttons. A wheel-only zoom is unusable without a mouse and
  invisible to anyone who does not think to try.
- **The viewer renders without a result.** Before any head has run, the right pane shows the
  image with an empty-state message rather than collapsing the layout — otherwise the panes
  jump sideways the first time a prediction arrives.

## Data Flow

Greenfield — no existing values are consumed or transformed. The image path comes from
doc 17's `useImageSource`; nothing else crosses this boundary.

## Dependencies

`17-image-input-source` for the current item. `lib/geometry.ts` (from doc 05) for
`fitContain`. Deliberately **not** doc 16 or 18: this feature never sees a prediction.

## Security

None. No input is accepted, no path is read, nothing is stored. The image bytes arrive
through the endpoint doc 17 already documented.

## Two bugs the unit tests could not have caught

Both were found by driving the running app, and both are the same shape: **jsdom reports
every element as 0×0**, so a clamp computed against a wrong-but-zero box behaves
identically to a clamp against a correct one. Recorded because the class will recur in
features 20 and 21.

1. **The clamp measured the whole component, not a pane.** `frameRef` sat on the outer
   element (688×320) while the pane frames are 338×254, so the pan bounds were roughly
   twice too generous and the image could be dragged off its own frame — precisely the
   failure the invariant exists to prevent. The regression test stubs
   `HTMLElement.prototype.clientWidth` *before* mount, because the measurement happens in a
   mount effect, and asserts the drag stops at exactly `-75` rather than merely "somewhere
   sensible". Confirmed to fail against the pre-fix code.
2. **Double-clicking a control reset the view.** `onDoubleClick` was on the outer
   container, so clicking "Zoom in" twice quickly — an entirely natural action — bubbled a
   `dblclick` and threw the zoom away. The gestures now live on the pane frames, which is
   also the box the clamp is computed against, so both bugs had the same fix.

A third, smaller one came out of a screenshot: the empty-state message was inside the
transform and grew with the zoom. An overlay belongs to the image and must scale; chrome
must not. The pane now takes both, in different places.

## Verified

In the running app, on the 900×300 panorama:

```
frame            338 x 254
zoom 3 steps  →  195%,  both panes' transforms byte-identical
drag -9000px  →  translate(-190.125px, -142.875px)   = exactly 338(1-1.5625), 254(1-1.5625)
dblclick control →  no reset      dblclick image →  back to 100%
placeholder      13.6px at 195% zoom (outside the transform)
```

## Known Issues

- **Zoom is about the stage box, not the image content inside it.** With `object-fit:
  contain` the two differ on a letterboxed image, so zoom-at-cursor drifts slightly from
  the pixel under the pointer. Both panes drift identically and the overlay shares the same
  `fitContain` geometry, so nothing misaligns — the gesture is just looser than it should
  be. The fix is to size the stage to the rendered image rather than to the frame.
- **`aspect-ratio: 4 / 3` on the frame is a fixed guess.** A very wide or very tall image
  wastes a lot of pane. Sizing the frame from the image's own aspect ratio needs the natural
  size before first paint, which is why it was not done here.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

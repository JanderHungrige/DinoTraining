---
id: 28-mask-review-ui
title: Mask Review UI — Verdicts on Masks, Beside the Box Canvas
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [27-grounded-sam-annotator, 26-generator-review-ui, 20-inference-overlay-render]
relates: [05-annotation-canvas, 22-mask-dataset-store]
source_files:
  - apps/frontend/src/components/MaskReviewCanvas.tsx
  - apps/frontend/src/components/overlays/MapOverlay.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/api/generate.ts
  - apps/frontend/src/api/annotators.ts
  - apps/frontend/src/types/annotation.ts
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/MaskReviewCanvas.test.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.test.tsx
  - apps/frontend/src/components/GeneratorSetup.test.tsx
  - apps/frontend/src/hooks/useGeneratorSession.test.ts
data_flow: reads-existing
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [mask-review, verdicts, canvas, accessibility, grounded-sam, dataset-generator]
path: Dataset Generator/Review
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Reviewed masks cannot be saved yet — that is 29-generated-dataset-writer. The tab says so in place of a disabled Save button."
security_read_sites: []
---

# 28 — Mask Review UI

## Purpose

Per-mask accept / reject / unclear over the image, so SAM's proposals become reviewed
training targets. With `27-grounded-sam-annotator` beneath it this is the first point in
the wave where the whole loop runs: a concept goes in, masks come back, and a person judges
them.

## A sibling, not an extension

`AnnotationCanvas` owns drawing, dragging and resizing rectangles. None of that applies to
verdict-only mask review, and that file is already at the project's size limit. Folding
masks in would have put a second geometry model in it, and every future box change would
have had to reason about masks it never touches.

What the two share is the part that must not diverge: the same three verdicts, the same
click-to-cycle gesture, the same 1/2/3 keys, and real focusable buttons.

**The mask's bounding box is the hit target.** Mask pixels are awkward to click and
impossible to focus; the box — derived server-side in doc 27, so nothing here decodes an
RLE — gives a control that behaves exactly like the box canvas's, and brings keyboard
operation and the accessibility tree with it.

**There is no Delete.** A rejected mask is `negative`, which is information the trainer can
use; removing it would throw that away silently.

## `MapOverlay` gained an alpha function

The existing overlay painted **every** pixel opaque, which is right for a class-index map
where every pixel belongs to some class. A binary instance mask is the other case: value 0
means "not this object", and painting it opaque covers the image with a rectangle instead
of showing one shape.

`alphaFor` defaults to fully opaque, so the Wave 3 viewer is unchanged. Extending the one
canvas rather than writing a second is what its own docstring argues for.

## The bug this feature surfaced

Driving the tab in **light mode** showed verdict tags as blank dark rectangles. Measured
rather than eyeballed: text `rgb(6,18,31)` on background `rgb(5,15,26)` — a contrast ratio
of **1.11**.

The cause is subtle and pre-dates this wave. `.canvas__boxtag` built its background from
`color-mix(in srgb, currentColor 85%, #000)` — but it also sets its own near-black `color`,
and **`currentColor` resolves against the element's own computed colour**, not its parent's.
So the mix was near-black on near-black. It had never been verdict-coloured; it merely
looked acceptable in dark mode because the tag sat on a dark background anyway.

Fixed with a custom property, which *does* inherit: each `.canvas__box--<verdict>` sets
`--verdict`, and both the border and the tag background read it. Contrast after the fix:

| verdict | before | after |
|---|---|---|
| positive | 1.11 | **10.82** |
| negative | 1.11 | **6.81** |
| unclear | 1.11 | **11.29** |

**This is a Wave 1 bug in the Annotation Studio**, not a Wave 4 one — the box canvas has
the same tag. It went unnoticed because the app is dark-first and nobody had run it in
light mode.

## The console warning that was not a bug

The browser console showed a React *Rules of Hooks* violation for `DatasetGeneratorTab`,
hook 13 changing from `useRef` to `useState`. That is exactly what adding a `useState` to
`useGeneratorSession` looks like **across an HMR boundary**: the "Previous render" column
described the pre-edit module, which a fresh page cannot produce.

Restarting the dev server did not clear it, because the console history is retained per
tab — so console archaeology could not settle it either way. `DatasetGeneratorTab.test.tsx`
now asserts that a fresh render produces **no `console.error` at all** on this path,
including hook-order messages. That is a durable answer where reasoning was not.

It is also the handoff's standing advice, applied: *verify with tsc and the rendered page,
not the console.*

## Two review surfaces, chosen by config

The tab renders the mask canvas or the box canvas from **`config.kind`**, not from which
array happens to be populated. An empty mask list must still show the mask canvas, or
"found nothing" would silently render the box canvas instead and look like a mode switch.

`GeneratorConfig` became a discriminated union for the same reason: an expert head needs a
backbone and an instance, a mask annotator needs a concept and an annotator id, and neither
set means anything to the other.

## Verified end to end

Through the browser, against real Grounding DINO + SAM 2.1 on MPS, over a folder of two
scenes:

- concept `"a red circle. a blue square."` → two masks, correct shapes, correct spans
- clicking a mask cycled it to **Negative** and its tag turned red
- pressing `3` on a focused mask set it to **Unclear**, tag amber
- verdict colour propagates to the mask tint, the outline and the tag together

## Known Issues

See frontmatter: saving arrives with the next feature.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

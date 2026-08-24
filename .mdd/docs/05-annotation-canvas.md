---
id: 05-annotation-canvas
title: Annotation Canvas — Box Overlay, Labelling & Drawing
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-1
wave_status: complete
depends_on: [01-app-shell]
relates: [06-annotation-workflow]
source_files:
  - apps/frontend/src/types/annotation.ts
  - apps/frontend/src/lib/geometry.ts
  - apps/frontend/src/components/AnnotationCanvas.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/lib/geometry.test.ts
  - apps/frontend/src/components/AnnotationCanvas.test.tsx
data_flow: greenfield
last_synced: 2026-08-17
status: complete
phase: all
mdd_version: 11
tags: [canvas, bounding-boxes, labelling, keyboard-shortcuts, accessibility, react]
path: Studio/Canvas
integration_contracts:
  - function: toNatural(rect, scale) / toDisplay(box, scale)
    when: converting between displayed pixels and image-natural pixels
    applies_to: annotation-workflow, dataset-generator
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "Boxes cannot be moved or resized after creation — a wrong box must be deleted and redrawn. Acceptable for the accept/reject loop Wave 1 targets; add drag handles when the dataset generator (Wave 4) does heavier correction work."
  - "No undo. The component is controlled and never mutates, so the parent can add history; nothing does yet."
  - "Overlapping boxes: the topmost in DOM order wins the click. Fine at Grounding DINO densities; needs a z-order or cycle-through if a prompt ever returns dozens of overlapping proposals."
  - "Visual rendering verified via 06-annotation-workflow, which is what mounts the canvas; feature 05 itself has no route to open."
  - "FIXED 2026-08-19 (Wave 4): the verdict tag was invisible in light mode. .canvas__boxtag built its background from color-mix(currentColor 85%, #000) while also setting its own near-black color — and currentColor resolves against the element's OWN computed colour, not its parent's — so the mix was near-black on near-black, contrast ratio 1.11. The tag had never actually been verdict-coloured; the app being dark-first merely hid it. Fixed with an inheriting --verdict custom property set on .canvas__box--<label>, read by both the border and the tag background; contrast is now 6.8-11.3 across the three verdicts. Found by running the Dataset Generator in light mode, not by any test."
sister_projects: []
---

# 05 — Annotation Canvas — Box Overlay, Labelling & Drawing

## Purpose

The screen the user actually spends their time in: an image with boxes drawn over it,
each one a click or a keystroke away from being positive, negative or unclear. Pure
UI — it takes boxes and emits boxes, and knows nothing about HTTP or datasets, so the
Wave 4 dataset generator can reuse it unchanged.

## Architecture

**DOM overlay, not `<canvas>`.** Each box is a real focusable `<button>` positioned
over the image. A `<canvas>` would need a parallel accessibility tree, hit-testing by
hand, and its own focus model; the DOM gives all three for free, and at the tens of
boxes this app produces there is no performance reason to give that up.

```
<figure>                    position: relative
  <img>                     the image, object-fit: contain
  <div class="overlay">     absolutely positioned, matches the rendered image box
    <button class="box">    one per box — focusable, aria-labelled
    <div class="draft">     the rectangle being dragged, if any
```

**Two coordinate spaces.** Boxes are stored in image-natural pixels (what the backend
and dataset store use). The overlay works in displayed pixels. `geometry.ts` owns both
conversions and nothing else converts — a second conversion site is how boxes end up
subtly offset only on scaled displays.

## Data Model

```ts
interface CanvasBox {
  id: string;              // client-side identity, so React keys survive relabelling
  label: 'positive' | 'negative' | 'unclear';
  provenance: 'grounding-dino' | 'hand-drawn';
  x: number; y: number; w: number; h: number;   // image-natural pixels
  score?: number;
  text?: string;
}
```

## Business Rules

- **Click cycles the label** positive → negative → unclear → positive. Cycling beats a
  menu: the user is making the same three-way call hundreds of times, and a click
  costs one action instead of three.
- **Keyboard shortcuts** on the focused box: `1`/`p` positive, `2`/`n` negative,
  `3`/`u` unclear, `Delete`/`Backspace` removes, `Escape` deselects. Tab moves between
  boxes because they are real buttons in document order.
- **Drag on empty space draws a new box**, labelled `positive` and `hand-drawn`.
- **A drag under 5×5 displayed pixels is discarded** as a stray click, not stored as a
  degenerate box the backend would reject anyway.
- **New boxes are clamped to the image bounds**, so a drag that leaves the frame still
  produces a valid box rather than a 422 on save.
- **Nothing is mutated in place.** The component is controlled: it emits a new array
  and the parent owns the state, so undo and dirty-tracking stay possible.

## Data Flow

`label` — set here by click or keystroke → emitted through `onBoxesChange` → held by
`annotation-workflow` → sent to `PUT /datasets/{id}/images`. The canvas never talks to
the backend itself; that separation is what lets Wave 4 reuse it.

## Dependencies

- `01-app-shell` — styling tokens and the tab that hosts it. No API dependency by design.

## Security

No network access, no filesystem access, no `dangerouslySetInnerHTML`. The `text` field
on a box originates from the model and is rendered as a text node, so a prompt echoed
back cannot become markup.

## Known Issues

(none yet)

## Bugs

(none yet — populated by /mdd bug when issues are reported)

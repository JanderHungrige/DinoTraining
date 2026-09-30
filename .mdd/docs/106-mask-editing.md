---
id: 106-mask-editing
title: Mask Editing — SAM Clicks, Brush and Eraser, Undo, and Outlines from Boxes
edition: DinoTraining
depends_on: [22-mask-dataset-store, 61-studio-masks, 104-annotation-target]
relates: [105-phrase-annotation-ux, 94-sam2-finetune]
source_files:
  - backend/app/ml/segmenter.py
  - backend/app/ml/mask_strokes.py
  - backend/app/api/v1/segment.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/segment.ts
  - apps/frontend/src/hooks/useMaskEditing.ts
  - apps/frontend/src/components/MaskEditOverlay.tsx
  - apps/frontend/src/components/MaskEditBar.tsx
  - apps/frontend/src/components/AnnotationCanvas.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
  - apps/frontend/src/maskedit.css
  - apps/frontend/src/components/StudioViewBar.tsx
  - apps/frontend/src/components/StudioActions.tsx
  - apps/frontend/src/components/overlays/CompositedMasks.tsx
routes:
  - POST /api/v1/segment/refine
  - POST /api/v1/segment/boxes
  - POST /api/v1/segment/stroke
models: []
test_files:
  - backend/tests/test_mask_strokes.py
  - backend/tests/test_segment_api.py
  - apps/frontend/src/hooks/useMaskEditing.test.tsx
  - apps/frontend/src/components/MaskEditBar.test.tsx
  - apps/frontend/src/components/overlays/CompositedMasks.test.tsx
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, masks, sam2, brush, eraser, undo, point-prompts, webkit]
path: Annotation Studio/Mask editing
initiative: dinotraining
wave: dinotraining-wave-14
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "'Outlines from my boxes' works on the picture in view; a whole dataset at once is left to a later job (it is a SAM 2 pass per picture)."
  - "Must be verified in the packaged desktop app too: WebKit dithers PNG-transported data (memory dinotraining-webkit-canvas-data). Editing is done on the server and returned as RLE + PNG, the path the Studio already renders."
security_read_sites:
  - "backend/app/api/v1/segment.py: image_path read through app.ml.images.read_image (format-checked, the project's one reader of user paths)"
sister_projects: []
---

# 106 — Mask Editing

## Purpose

Until now an outline came only from a model and could not be corrected: a wrong pixel
meant rejecting the whole outline. SAM 2 and SAM 3 fine-tuning learn *your* convention
(doc 94's filled rings), so the convention has to be something you can draw.

Wave 14 needs three things:
- **click refinement,** the fast path;
- **brush and eraser,** for the last pixels;
- **outlines from boxes,** so a box dataset becomes a SAM dataset.

## Measured before writing (2026-09-30, SAM 2.1 small, M1)

Two touching discs, and a box around both.

| Prompt | Left disc | Right disc |
|---|---|---|
| box | 5 115 px | 5 128 px |
| box + ⊕ on left | 5 132 | 5 127 |
| box + ⊕ left + ⊖ right | 5 127 | **21** |

The call format is: `input_boxes=[[box]]`, `input_points=[[points]]`,
`input_labels=[[labels]]` (image → object → point). Three calls took 3.1 s including the
model load; a warm call is well under a second.

## Tools (a bar shown while an outline is selected)

| Tool | Does | Server |
|---|---|---|
| **⊕ Add** | A click adds a positive point; SAM 2 redraws the outline from the box plus every point so far | `POST /segment/refine` |
| **⊖ Remove** | The same with a negative point | same |
| **Brush / Eraser** | A drag paints or erases with the chosen size | `POST /segment/stroke` (numpy, no model) |
| **Undo** | Back one edit (up to 20) | — |
| **Outlines from my boxes** | Every positive box on this picture without an outline gets one (SAM 2, box prompt) | `POST /segment/boxes` |

- **Clicking ⊕ on a box without an outline** makes one: the box plus the point. That is the
  per-box "make an outline".
- **Points belong to the selected outline** and are forgotten when the selection changes;
  a fresh click starts from the box.
- **Every edit is a canvas edit:** the picture becomes unsaved, and Save writes it (doc 61's
  path). Outlines from boxes are proposals, reviewed like any other.

## Why the server does the pixels

- **The WebKit trap:** WebKit dithers pixel data carried through a canvas (memory
  `dinotraining-webkit-canvas-data`), so a mask edited in a canvas could differ from what
  was drawn.
- **The server path:** `mask_strokes.py` decodes the RLE, stamps discs along the stroke,
  and encodes it again. It returns RLE plus PNG, which is exactly what the Studio already
  renders for stored masks.
- **Tests:** the arithmetic sits beside the store's own RLE code and is tested there.

## API

**Each route returns an `EditedMask`:** `{rle: {size, counts}, mask_png, x, y, w, h,
score|null}`.

| Route | Takes |
|---|---|
| `POST /segment/refine` | `{image_path, box {x,y,w,h}, points [{x, y, positive}], model_id?}` |
| `POST /segment/boxes` | `{image_path, boxes [{x,y,w,h}], model_id?}` → `{masks: [...]}`, one per box, in order |
| `POST /segment/stroke` | `{rle, points [[x, y], …], radius, erase}` |

**Refusals:**
- a missing image → 404, and a model that is not installed → 404, which names Admin;
- an outline an eraser would empty → 422, *"Nothing would be left of this outline — reject
  it instead"*;
- points or a box outside the picture → 422.

## Business Rules

1. **Coordinates are the picture's own pixels,** like every stored annotation.
2. **The box of an edited outline is its new extent,** derived by the server.
3. **The model is `sam2.1-hiera-small` unless given,** the one the starter set installs.

## Found live: an outline edited in place was not redrawn

- **The symptom:** after ⊖ on the centre of a filled ring, the server returned a ring with
  a hole (the RLE alternates 22 on, 10 off, 23 on down the middle columns), and the Studio
  marked the picture unsaved. The canvas still showed the filled disc.
- **The cause:** `CompositedMasks` redraws when its *signature* changes, and the signature
  held each mask's id, verdict, selection and colour, but not its picture. An edit keeps the
  id, so nothing redrew.
- **The fix:** the signature now includes a fingerprint of the PNG (FNV-1a).
- **The test:** it repaints the same id with a new PNG. It fails without the fix and passes
  with it.
- **Checked live afterwards:** the canvas pixel at the ring's centre went from painted to
  transparent.

The Studio reached the 300-line gate; its view bar and action row moved to `StudioViewBar`
and `StudioActions`.

## Verified (2026-09-30)

- **Tests:** backend 1755 green, frontend 1024 green, tsc clean.
- **Running app, "Wave 12 filled-ring convention", ring 2 selected (nothing saved):**
  - **⊖ Remove** on its centre: SAM 2 returned the ring with a hole (score 0.977), and the
    canvas showed the hole.
  - **Brush** dragged across the hole filled it again.
  - **Undo** twice gave first the hole, then the original filled disc, and then Undo was
    disabled.
  - The page was reloaded without saving.

## Bugs

(none yet)

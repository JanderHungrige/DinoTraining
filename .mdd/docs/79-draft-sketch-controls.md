---
id: 79-draft-sketch-controls
title: Draft Sketch Controls — NinaNatur's Hand-Drawn Buttons
edition: DinoTraining
depends_on: [78-lato-typography, 77-app-background-layer]
relates: [80-legibility-and-motion-pass]
source_files:
  - apps/frontend/src/look.css
  - apps/frontend/src/components/TokenPanel.tsx
routes: []
models: []
test_files: []
data_flow: greenfield
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [look-and-feel, buttons, accessibility, reduced-motion, css]
path: App Shell/Look & Feel
initiative: dinotraining
wave: dinotraining-wave-10
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "At device-pixel ratio 1 the 1.5 px line renders as 1 px, measured here: `borderTopWidth: 1px`, with the same rounding NinaNatur gets. On a Retina display it is 1.5 px. The shadow and the edge carry the look either way."
  - "On very wide buttons (Start generating is full width) the 255px radii are clamped by the browser, so the hand-drawn wobble reads mostly at the corners. That is the same geometry NinaNatur uses." 
security_read_sites: []
sister_projects: [/Users/jwh/Code/NinaNatur]
---

# 79 — Draft Sketch Controls

## Purpose

Requested: *"For the buttons use the button outline look from our project ninanatur."* Jan
chose **Draft Sketch**: `~/Code/NinaNatur/frontend/src/themes/draft-sketch/ours/controls.css`,
at NinaNatur commit `1a5ad29`.

## What is taken, and what is adapted

| NinaNatur (Draft Sketch) | Here | Why |
|---|---|---|
| Edge `255px 14px 225px 16px / 16px 225px 14px 255px` | same | This edge is the look. |
| 1.5 px line, `aria-pressed` 2.5 px | same | |
| Offset shadow 1px 2px at 40 % ink | same, at 35 % | |
| Hover: deeper wash, turn −0.6° | same | |
| Active: shadow off, press 1px 2px | same | |
| Ink `#1c2419` on paper | **`var(--text)`** | Black ink vanishes on the dark, moving background. `--text` is light in dark mode and dark in light mode, so the ink always reads. |
| Grass wash `#8fbf6a` on paper | **translucent `--bg-raised`, the app's accent for primary** | The app's green accent plays the role NinaNatur's grass does: "the button that does something". |
| Patrick Hand | **Lato** (doc 78) | Jan asked for Lato. |

## Business Rules

1. **Scope is `.btn` and every variant** (`--primary`, `--small`, `--danger`, the Stop
   button). That is all but a handful of the app's buttons.
   - **Deliberately not:** tabs, the timeline's rows, review verdict chips, and the box and
     mask buttons drawn over images. Those are not "buttons" to the eye, and a wobbly
     outline over an annotation would compete with the box it marks.
2. **Focus is never removed.** The global `:focus-visible` outline stays and follows the
   edge.
3. **Reduced motion:** no turn, no press, no transition. The outline and wash stay.
4. **Disabled:** no shadow, no motion, faded ink. A disabled control must not look
   pressable.
5. **Provenance** is noted at the top of the CSS block, as NinaNatur does it.

## Verified in the running app (2026-09-29)

- **Computed on a `.btn`:** edge `255px 14px 225px 16px / 16px 225px 14px 255px`, Lato,
  shadow `… / 0.301 1px 2px`, and a translucent wash.
- **Admin, screenshot:** "Remove" has the light ink outline and offset shadow on the blurred
  background. The disabled "Save token" is clearly faded, with no shadow.
- **Generator setup, screenshot:** "Start generating" (primary) carries the green wash with
  the ink outline.
- TokenPanel's two unstyled buttons now use `.btn`, so no button in Admin is left in the
  browser default.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

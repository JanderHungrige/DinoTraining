---
id: 157-sketch-everywhere
title: Sketch Everywhere — Fields, Boxes and Tabs in the Buttons' Hand, One Look in Both Schemes, Admin Panels Full Width
edition: DinoTraining
depends_on: [79-draft-sketch-controls, 80-legibility-and-motion-pass]
relates: [77-app-background-layer, 57-gpu-panel]
source_files:
  - apps/frontend/src/sketch.css
  - apps/frontend/src/main.tsx
  - apps/frontend/src/look.css
  - apps/frontend/src/styles.css
  - scripts/check_background_contrast.py
routes: []
models: []
test_files:
  - apps/frontend/src/sketch.test.ts
data_flow: greenfield
last_synced: 2026-10-01
status: complete
phase: all
mdd_version: 11
tags: [look-and-feel, draft-sketch, css, dark-theme, contrast, admin]
path: UI/Look/Sketch
initiative: dinotraining
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 157 — Sketch Everywhere

## Jan (2026-10-01)

- "I see a mix of sketch buttons and other element optics. Please make all (as suitable)
  also sketch."
- "In the light mode, the background is too bright. Maybe just use the original."
- "The using GPU box is shorter than the others. Looks bad. Please check the layout."

## 1. Sketch beyond the buttons (`sketch.css`)

- **The same hand as doc 79:** the ink `--sk-ink`, the line, the offset shadow.
- **Fields** (text, number, search inputs, selects): the button's edge, mirrored, a softer
  ink that darkens on hover, a faint inset line. Textareas take the box edge (tall).
  Checkboxes, radios and sliders keep their native shape in the accent colour.
- **Boxes** (every card and panel: setup, settings, Admin panels, guides, cards, notices,
  import/export panels…): a gentler hand-drawn edge (`--sk-edge-box`), a 1.5 px line and a
  soft offset shadow. **Their border colours stay:** they mean something (warning, GPU,
  starter set).
- **Tabs:** the open main tab and the open sub-tab are drawn round like a pressed primary
  button (heavy ink, green wash); the others are only written, with a pen line on hover.
- **Small controls that are buttons to the eye:** phrase chips, the preparation steps,
  rename, parameter reset and "?" (still round).
- **Still not drawn, as doc 79 decided:** the canvas, player and anything over an image
  (box and mask buttons, review verdicts, timeline rows), code blocks, pictures.
- **Loaded after `look.css`;** equal specificity wins by order. No component CSS is lazy,
  so nothing loads after it.

## 2. One look in both schemes

- **The light scheme washed the loop to a pale peach.** Its dark text needs a near-white
  surface, and the panel is page-wide, so "light" can only ever be bright.
- **Measured first:** doc 80's script checked the brightest pixel only. Over the darkest
  (`[0, 5, 16]`) the light scheme failed AA in four colours (dim 3.52, accent 2.95, danger
  3.81, pending 3.50). Keeping a light scheme over the original loop needed panels at 80 %
  and darker colours, which is brighter still.
- **So the app keeps its original, dark look in both OS schemes** (the shell was
  "dark-first" from the start). The light token blocks are gone from `styles.css` and
  `look.css`.
- **The script now checks the brightest and the darkest pixel:** every colour ≥ 5.08:1.

## 3. Admin panels full width

- **The GPU panel and the distribution notice had `max-width: 72rem`;** every other Admin
  panel spans the column, so on a wide window those two ended short. Both now span it,
  with the same padding and spacing (1.5 rem below) as their neighbours.

## Tests

- `sketch.test.ts`:
  - no stylesheet carries a light-scheme override;
  - `sketch.css` is imported after `look.css`, which comes after `styles.css`;
  - every class `sketch.css` draws still exists in another stylesheet, so a renamed class
    cannot silently lose its sketch.
- `scripts/check_background_contrast.py` passes over both extreme pixels.

## Verified in the running app (2026-10-01)

- **The OS in light mode:** the dark bokeh shows, as in dark mode.
- **Annotation Studio:** the setup box, its two choice boxes, the dataset select and the
  prompt field carry the hand-drawn edge; the open tab is drawn round with the green
  wash.
- **Models & Datasets:** the open main tab and the "Datensätze" sub-tab are drawn like
  primary buttons; the uninstall notice is a sketch box.
- **Admin at 1400 px:** a stand-in GPU panel is 1352 px wide, as are the system, token,
  starter and distribution panels (it was 1152 px before).

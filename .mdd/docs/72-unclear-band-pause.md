---
id: 72-unclear-band-pause
title: Ask When Unclear — Autoplay Pauses on a Score Band
edition: DinoTraining
depends_on: [71-generator-autoplay, 69-remembered-entries]
relates: [70-generator-action-bar, 28-mask-review-ui, 47-box-review-list]
source_files:
  - apps/frontend/src/lib/unclearBand.ts
  - apps/frontend/src/lib/autoplay.ts
  - apps/frontend/src/hooks/useAutoplay.ts
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/types/generatorSession.ts
  - apps/frontend/src/components/UnclearBandField.tsx
  - apps/frontend/src/components/UnclearQuestion.tsx
  - apps/frontend/src/components/AutoplayProgress.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/lib/unclearBand.test.ts
  - apps/frontend/src/lib/autoplay.test.ts
  - apps/frontend/src/components/UnclearBandField.test.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.autoplay.test.tsx
data_flow: writes-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [dataset-generator, autoplay, uncertainty, review, active-learning, accessibility]
path: Dataset Generator/Autoplay
initiative: dinotraining
wave: dinotraining-wave-9
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "There is no default band that suits every model. Scores are not calibrated across Grounding DINO, RF-DETR, SAM and trained heads, so the band is the user's and the default (0.30–0.50) is only a starting point. Remembering a band per model would be the next step if switching models turns out to be common."
  - "The question appears below the canvas. On a small window the page scrolls to it, because Continue takes focus. On a tall image the question and the boxes can still be a scroll apart."
security_read_sites: []
sister_projects: []
---

# 72 — Ask When Unclear

## Purpose

Requested: *"add a checkbox to ask the user during auto mode if a prediction is unclear
(user set the boundaries)."*

Autoplay (doc 71) is only as good as the proposals it saves without looking. The
predictions worth a human's second are neither confident hits nor obvious misses: they
are the middle of the score range. This feature spends the reviewer's attention only there.

## Business Rules

1. **Off by default; the band is the user's** (`generator.askUnclear` and
   `generator.unclearBand`, remembered per doc 69). The default band is 0.30–0.50.
   Bounds typed the wrong way round are put back in order, and out-of-range bounds are
   clamped. The band is inclusive at both ends.
2. **A proposal with no score never asks.** It cannot be judged against a band.
3. **When any proposal on an image falls in the band, autoplay pauses on that image.**
   - The in-band proposals are relabelled **unclear**, so they stand out (dashed) and so an
     unanswered question saves as *unclear*, never as the model's guess. Out-of-band
     proposals keep the model's verdict.
   - Hidden mode shows the image for the question and returns to hidden afterwards.
4. **The canvas is the user's during the question; nothing else is.** Click cycles a label,
   and 1 / 2 / 3 set it on a focused box. The toolbar stays locked, apart from Stop.
5. **Continue saves the image as it now stands on screen**, via the session's
   `currentReview()`, with edits included, and then carries on. The 0.5 s hold is skipped:
   the user has already looked.
6. **Stop here** (or the toolbar's Stop) ends the run on that image, unsaved. A run parked
   on a question is waiting on a promise the abort signal cannot reach, so Stop settles
   the question too.
7. **The question takes focus** (Continue) and is a `role="alert"` region named "Autoplay
   is waiting for you". A run that pauses by itself must be announced.
8. **The summary counts questions** ("1 asked about"), and each asked image also counts
   as saved.

## Verified in the running app (2026-09-29)

Grounding DINO tiny, "a chess piece.", band 0.25–0.40, over the chess folder:

- Autoplay paused on **image 3** after 4.7 s. The whole-board box (a false positive,
  score 34 %) was marked *unclear*, the piece (63 %) stayed *positive*, and **Continue
  had focus**.
- The box was focused and marked negative with **2**, then Continue was pressed. The run moved
  on to image 4, and the counter's Negative went 0 → 1.
- **Direct read of the dataset:** that image stored
  `[('positive', 0.63), ('negative', 0.34)]`, which is the user's verdict, not the model's.
- After Stop, the summary read "5 saved · 0 with nothing found · 1 asked about".

## Bugs

(none yet — populated by /mdd bug when issues are reported)

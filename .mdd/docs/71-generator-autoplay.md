---
id: 71-generator-autoplay
title: Generator Autoplay — Propose, Hold, Save, Next
edition: DinoTraining
depends_on: [70-generator-action-bar, 69-remembered-entries]
relates: [53-prescan, 66-prompted-detection-everywhere]
source_files:
  - apps/frontend/src/lib/autoplay.ts
  - apps/frontend/src/hooks/useAutoplay.ts
  - apps/frontend/src/hooks/useGeneratorImages.ts
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/hooks/useAutoPropose.ts
  - apps/frontend/src/lib/generatorProposal.ts
  - apps/frontend/src/types/generatorSession.ts
  - apps/frontend/src/components/AutoplayControls.tsx
  - apps/frontend/src/components/AutoplayProgress.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/lib/autoplay.test.ts
  - apps/frontend/src/hooks/useAutoplay.test.ts
  - apps/frontend/src/components/AutoplayControls.test.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.autoplay.test.tsx
data_flow: writes-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [dataset-generator, autoplay, automation, review, progress, react]
path: Dataset Generator/Autoplay
initiative: dinotraining
wave: dinotraining-wave-9
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Leaving the Generator tab stops a run. Tabs unmount (App renders only the active one), and a run with nothing on screen to stop it would keep proposing and saving. The setup is remembered (doc 69), and images saved this session are skipped when Play is pressed again. Images saved in an *earlier* session are re-proposed, though, because the session only knows what it saved itself."
  - "Hidden mode is barely faster on this machine. It skips drawing and the 0.5 s hold, but the proposal dominates: Grounding DINO tiny on MPS took about 1.3 s per 640 px image once warm, and 8–12 s for the first call."
  - "An image where nothing was found is not written, which matches the manual Save (doc 70, rule 4). A dataset built by autoplay therefore holds no explicit negatives; the counter's 'with nothing found' is where they are counted."
security_read_sites: []
sister_projects: []
---

# 71 — Generator Autoplay

## Purpose

Requested: *"add an autoplay button. All steps are automated. After drawing the bounding
box, wait for 0.5s for the user to see the proposed bounding box. Make it stopable to
enable the user to return and correct a false bounding box prediction. When hit play, kick
off from the currently chosen image. Have a 'hidden' checkbox, that goes through the image
automatically, without waiting or drawing the image. Just show a percent bar."*

## Architecture

```
AutoplayControls  [▶ Play] / [■ Stop]  [☐ hidden]  12 / 243        in the doc 70 toolbar
        │
useAutoplay(config, session)   React side: running, progress, report; stops on unmount
        │ reads the session through a ref to its *latest* render
        ▼
runAutoplay(run)  lib/autoplay.ts — a plain async loop over paths, outside React
   for each image from session.index:
     saved this session? → skip (counted)
     show(i, null)          visible: move there            (hidden: nothing)
     review = propose(path) — proposeReview(), straight to the API
     show(i, review)        visible: draw it
     nothing found?         → count "empty", do not write, next
     hold 500 ms            visible only; Stop here = "that one is wrong"
     save(review)           session.save(review): writes and remembers it
AutoplayBar       hidden mode's percentage, in place of the canvas
AutoplaySummary   why the run ended, and what it did
```

**Why the loop is outside React.** After every `await`, a component's state is stale. A loop
that called `session.propose()` and then `session.save()` would propose for the image in
the closure and save whatever state had rendered, which is the previous image's boxes under
the next image's path. The loop owns its position and passes each result on explicitly.
That is also why doc 70 made `save` accept a review.

`useGeneratorImages` was split out of the session to make room: "which images" (listing,
prescan filter) on one side, "what happens on one image" on the other.

## Business Rules

1. **Play starts at the image on screen** and runs to the last image of the current list,
   so a prescan filter (doc 53) narrows autoplay too.
2. **The 0.5 s hold applies only when something was found.** With nothing drawn, there is
   nothing to look at.
3. **Stop never saves the image it stops on.** A stop during the hold or during the proposal
   leaves that image's proposal on screen, unsaved, editable and marked dirty. From there,
   the user's own *Next* (auto-save, doc 70) writes the corrected version.
4. **Auto-propose stays quiet during a run and after a stop.** A second proposer racing
   the run would be a second opinion. After a stop, the image already has its proposal:
   the session's `proposedFor` tells auto-propose so, and re-proposing would replace the
   mistake the user stopped to fix.
5. **Images saved this session are skipped**, so Play after a correction resumes rather
   than redoes. They still count toward 100 %.
6. **One failed proposal does not end a run.** It is counted, and the last failure's message
   is shown in the summary. **A failed save does end it**, because the next save would fail
   the same way, and skipping on would leave unsaved work behind.
7. **Hidden mode** draws nothing and does not hold. It shows a `<progress>` with a percentage,
   and when it ends or is stopped it lands on the last image it worked on.
8. **Everything else is locked while running**: Propose, Save, Previous, Next, both auto
   boxes, the hidden box and the canvas. **Stop is never disabled.**
9. **The hidden choice is remembered** (`generator.autoplayHidden`, doc 69).

## Verified in the running app (2026-09-29)

Grounding DINO tiny, prompt "a chess piece.", over the 289-image chess folder:

- **Play from image 1:** it proposed, held and saved image by image. After warm-up that was
  about 1.8 s per image (≈ 1.3 s proposal + 0.5 s hold). The saved count went up *before*
  each move.
- **Stop during a hold** (the boxes had just appeared on image 46):
  - Saved images stayed at 45, and the proposal stayed on screen and editable, marked
    "Unsaved changes". Play came back.
  - No proposal was requested in the next 3 s, so rule 4 held.
- ***Next* from there** auto-saved image 46 (46 saved).
- **Hidden mode from image 47:** "1 % — running hidden, image 2 of 243" and rising, with no
  canvas boxes drawn. Stop landed on image 51 with the summary.
- **Found on the way** (fixed in its own commit, doc 66's bug list): the Generator offered
  Grounding DINO and then refused it, "does not predict boxes".

## Bugs

(none yet — populated by /mdd bug when issues are reported)

## Changes

- **2026-09-30 (Jan):** the autoplay button reads **"▶ Start analysis"** instead of "Play" (it read as playing back what was annotated), and the automation boxes moved to their own row below the buttons, named in full: **Auto-propose**, **Auto-save**, **Run hidden**. The prescan button lost its emoji.

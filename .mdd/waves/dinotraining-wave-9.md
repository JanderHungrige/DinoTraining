---
id: dinotraining-wave-9
title: "Wave 9: Generator Autopilot & Dataset Inspection"
initiative: dinotraining
initiative_version: 9
status: in_progress
depends_on: dinotraining-wave-8
demo_state: "In the Dataset Generator the user picks a video, presses Play and watches it propose and save frame by frame, stopping only on predictions inside their 'unclear' score band. They then open the dataset in 'Inspect datasets', play the annotated video with coloured per-class bars under it, and jump to a class's first annotation. Every path and name they typed is still there after a tab switch or a restart."
created: 2026-09-29
hash: 51ef0f72
---

# Wave 9: Generator Autopilot & Dataset Inspection

**Inserted 2026-09-29 at Jan's request, ahead of the website wave, which is now Wave 13.**
Wave 7.5 was inserted as a fractional wave so that nothing had to be renumbered. This time
Jan asked for the shift explicitly. All 40 references to the old Wave 9 in docs and source
comments were retargeted, and a grep for `wave[ -]9` came back empty before this file was
written.

## Demo-State

1. The user opens the Dataset Generator and picks a **video file** as the source.
2. They press **Play**. From the current frame on, the Generator proposes, holds each result
   on screen for 0.5 s, saves it and moves on. They can stop it at any frame and correct a
   bad prediction by hand.
3. With **ask when unclear** ticked, autoplay pauses only on predictions whose score falls
   inside the band they set, and asks them to decide.
4. With **hidden** ticked, it runs without drawing and shows a percentage bar.
5. **"Inspect what I just annotated"** switches to the new **Inspect datasets** tab with that
   dataset open. It plays the frames with their annotations and draws a coloured bar per
   class under the video. Clicking a bar and pressing **Jump to first** goes to that class's
   first annotated frame.
6. Every path, dataset name and prompt they typed survives a tab switch and an app restart.

*(This wave is not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | remembered-entries | docs/69-remembered-entries.md | complete | — |
| 2 | generator-action-bar | docs/70-generator-action-bar.md | complete | — |
| 3 | generator-autoplay | docs/71-generator-autoplay.md | complete | generator-action-bar |
| 4 | unclear-band-pause | docs/72-unclear-band-pause.md | complete | generator-autoplay |
| 5 | generator-video-source | docs/73-generator-video-source.md | complete | — |
| 6 | inspect-datasets-tab | docs/74-inspect-datasets-tab.md | complete | generator-video-source |
| 7 | annotation-timeline | docs/75-annotation-timeline.md | complete | inspect-datasets-tab |

### Feature notes

1. **remembered-entries.** Tabs unmount when you leave them (`App.tsx` renders only the
   active one), and no field is persisted anywhere. The fix is one `usePersistentState`
   hook backed by `localStorage`, with versioned keys and every read and write wrapped in
   try/catch. It goes on every path, dataset-name and prompt field: `SessionSetup`,
   `GeneratorSetup`, `ImageSourceField`/`ImageSourcePicker`, the Inference Viewer's path,
   `SequencePanel`, `PrescanPanel` and `FinetunePanel`.
   - **A remembered dataset id is an *override*, not a seed.** CLAUDE.md's React-state rule
     applies: the dataset may have been deleted since, so the effective value is derived as
     `override || items[0]?.id`, with a stored id that is no longer listed treated as absent.
   - **Not remembered:** running sessions and in-flight jobs. Only entries are.
2. **generator-action-bar.**
   - An **auto** checkbox beside *Propose* (on by default) proposes as soon as an image
     is shown that has nothing stored yet.
   - An **auto** checkbox beside *Save* (on by default) saves a dirty image when you
     leave it by *Next* or *Previous*. Leaving an image is the only moment "auto-save"
     cannot discard a correction that is still being made.
   - Both controls sit directly beside *Previous/Next*, with no spacer in between. The two
     preferences are remembered, which is feature 1's hook again.
3. **generator-autoplay.** A Play/Stop button. Play starts at the current image and loops
   propose → hold 0.5 s → save → next. Stop leaves the user on the image it was
   showing, which is fully editable.
   - **Hidden mode** skips drawing and the hold, and shows a progress bar with a percentage
     instead.
   - A run reports what it did: saved, empty and failed images.
   - One failed proposal is recorded and skipped rather than ending the run.
4. **unclear-band-pause.** An *ask when unclear* checkbox with a user-set score range
   `[low, high]`. When a proposal's score falls inside it, autoplay pauses on that image,
   marks those proposals, and waits. The user sets each one to accept, reject or unclear
   and then presses **Continue**. Hidden mode pauses the same way and shows the image for
   the decision.
5. **generator-video-source.** The Generator accepts a video file (doc 68's suffixes)
   next to a folder or a dataset.
   - The chosen range is decoded to JPEG files inside the dataset directory, as a job with
     progress, because the dataset stores image paths and the models read files.
   - A new `images.sequence` and `images.frame_index` (a migration) record which video, or
     which folder, a frame came from and where in it. That is what lets feature 6 play it
     back in order.
6. **inspect-datasets-tab.** A new tab that opens a dataset and plays its sequences with
   the stored annotations drawn over them (boxes, and masks per doc 67's view toggle). Loose
   images are stepped through instead.
   - The Generator gets **Inspect what I just annotated**, which switches tab *with* the
     dataset id. That is the first navigation with a payload, so it becomes a typed intent
     held in `App`.
   - The player reuses doc 68's `FrameCanvas`, drawing stored annotations rather than a run
     job.
7. **annotation-timeline.** One coloured bar per class under the player, marking the
   frames where that class has a positive annotation. It is served from one route that
   returns per-frame class presence for a whole sequence, so the bars do not need a
   request per frame.
   - Clicking a bar selects that class. **Jump to first**, plus previous and next
     occurrence, move the player.
   - The colours come from the same palette as the overlay, so bar and box agree.

## Open Research

- **Where autoplay runs.** It runs in the browser, which reuses propose and save
  unchanged. Because tabs unmount, leaving the Generator stops a run. Feature 3 must make
  that explicit, by stopping and saying so, rather than leaving the run half-dead.
  Feature 1 does not change this, because it keeps entries, not sessions.
- **Frame storage cost.** A 10-minute 1080p clip at 30 fps is 18,000 frames. At about
  250 KB per JPEG that is roughly 4.5 GB, so feature 5 needs a frame *stride* ("every Nth
  frame") alongside doc 68's start/count, and a size estimate shown before the click.
- **Score semantics for the unclear band.** Grounding DINO, RF-DETR, SAM and trained heads
  score on different scales. The band is per run and the UI names the model, but a
  default band that suits all of them may not exist.

---
id: 75-annotation-timeline
title: Annotation Timeline — Coloured Bars per Class, with Jumps
edition: DinoTraining
depends_on: [74-inspect-datasets-tab]
relates: [73-generator-video-source]
source_files:
  - apps/frontend/src/lib/timeline.ts
  - apps/frontend/src/components/AnnotationTimeline.tsx
  - apps/frontend/src/tabs/InspectTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/lib/timeline.test.ts
  - apps/frontend/src/components/AnnotationTimeline.test.tsx
  - apps/frontend/src/tabs/InspectTab.test.tsx
data_flow: reads-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [inspect, timeline, playback, navigation, accessibility, classes]
path: Inspect Datasets/Timeline
initiative: dinotraining
wave: dinotraining-wave-9
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "A bar marks where a class has a *positive* annotation. Unclear and negative annotations are not on it, matching what the player draws (doc 74)."
  - "Positions are places in the track's frame list, not time. For a video saved every Nth frame both are proportional; a moved folder that plays its annotated frames only would compress the empty stretches out of the bar as well as the playback."
  - "Clicking a bar selects its class; it does not seek. The request asked for select-then-jump, and a bar that also seeked would move the player on every selection. The scrub slider is where seeking lives."
security_read_sites: []
sister_projects: []
---

# 75 — Annotation Timeline

## Purpose

Requested: *"for videos have coloured annotation bars below the video, indicating where
which annotation can be found. Enable selecting an annotation bar by clicking and press a
button to jump to first annotation."*

## Architecture

```
DatasetPlayer (doc 74)
  … controls …
  AnnotationTimeline
    ■ signal  [██████      ███            █    ]   ← button, aria-pressed,
    ■ train   [      ████          ███████     ]      "signal: on 41 of 300 frames"
                         ▲ playhead
    signal:  [⇤ First] [◀ Previous] [Next ▶]
lib/timeline.ts   segmentsFor · classesIn · countFrames · first/next/previousOccurrence
```

The data is doc 74's `/sequences` route. Each frame carries its positive classes, and the
dataset's sorted `class_names` give each class one index, which is its colour here and on
the boxes over the frame.

## Business Rules

1. **One bar per class present in the track**, in the dataset's class order. A dataset
   class absent from this track gets no bar.
2. **Consecutive frames merge into one segment**, so a class seen for 300 frames is one
   element, not 300.
3. **A bar is a button.** Clicking selects its class (`aria-pressed`, outlined), and
   clicking again deselects it. Its accessible name says how often the class appears.
4. **The jumps apply to the selected class.**
   - *First* goes to its first frame.
   - *Previous* and *Next* go to the nearest occurrence on either side of the playhead,
     never wrapping, and are disabled when there is none.
   - Every jump pauses playback, so the frame jumped to stays on screen.
5. **The selection survives a change of track**, because "where is the signal in the next
   ride" is the natural next question. It is ignored in a track without that class.
6. **The playhead** marks the current frame on every bar.

## Verified in the running app (2026-09-29)

"Wave 9 video check": 30 frames, annotated at positions 0–2 (frames 0–4) and 8–10
(frames 16–20) by two autoplay runs.

- **The bar read** "a chess piece: on 6 of 30 frames", with two segments at 0 % (10 % wide)
  and 26.7 % (10 % wide), matching the two runs.
- **Clicking the bar** set `aria-pressed="true"`.
- **From "4 / 30 · frame 6 · not annotated", Next ▶** went to "9 / 30 · frame 16", the
  start of the second segment, with its 10 boxes drawn.
- **⇤ First** went to "1 / 30 · frame 0". Three presses of Next ▶ went 1 → 2 → 8.
- **Screenshot:** the frame with its boxes, the controls, and the red bar with both
  segments and the playhead inside the second.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

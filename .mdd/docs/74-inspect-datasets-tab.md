---
id: 74-inspect-datasets-tab
title: Inspect Datasets — Play a Dataset Back with Its Annotations
edition: DinoTraining
depends_on: [73-generator-video-source, 68-video-playback, 67-annotation-view-and-output]
relates: [50-dataset-as-source, 51-library-tab, 75-annotation-timeline]
source_files:
  - backend/app/datasets/sequences.py
  - backend/app/api/v1/dataset_images.py
  - apps/frontend/src/api/datasetSequences.ts
  - apps/frontend/src/tabs/InspectTab.tsx
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/tabs/introContent.ts
  - apps/frontend/src/App.tsx
  - apps/frontend/src/types/navigation.ts
  - apps/frontend/src/components/DatasetPlayer.tsx
  - apps/frontend/src/components/StoredOverlay.tsx
  - apps/frontend/src/components/FrameCanvas.tsx
  - apps/frontend/src/components/overlays/CompositedMasks.tsx
  - apps/frontend/src/hooks/useInspectData.ts
  - apps/frontend/src/hooks/useFrameMasks.ts
  - apps/frontend/src/hooks/usePlayback.ts
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/datasets/{dataset_id}/sequences
models: []
test_files:
  - backend/tests/test_dataset_sequences_api.py
  - apps/frontend/src/tabs/InspectTab.test.tsx
  - apps/frontend/src/hooks/usePlayback.test.ts
  - apps/frontend/src/components/StoredOverlay.test.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.autoplay.test.tsx
data_flow: reads-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [inspect, playback, dataset, video, frame-sequence, navigation, overlays]
path: Inspect Datasets
initiative: dinotraining
wave: dinotraining-wave-9
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Only positive annotations are drawn. Inspect shows what the dataset asserts; there is no toggle yet for seeing rejected or unclear proposals, which Review in the Studio still shows."
  - "Jumping here from the Generator unmounts it (tabs unmount), which ends that session and any autoplay. The button is therefore disabled while autoplay runs, and the Generator's setup is remembered (doc 69)."
  - "Unannotated frames on disk have no stored size. The player uses a saved neighbour's size, which is right for a video (constant size) and irrelevant when there is nothing to draw."
  - "Masks are fetched per frame (≈13 KB each, six ahead). A long mask-annotated sequence played at speed can outrun the fetch on a slow disk; the frame then shows without its masks rather than waiting."
security_read_sites:
  - backend/app/datasets/sequences.py:_on_disk (lists a stored sequence folder)
sister_projects: []
---

# 74 — Inspect Datasets

## Purpose

Requested: *"have an option to play the just now annotated video. But this happens in a new
tab: 'inspect datasets' (jumps to new tab and opens the dataset). There you can play your
annotated videos/images."*

## Architecture

```
Generator  [Inspect what I just annotated] ── onInspect(datasetId, video | folder | null)
                                   │  App holds an InspectRequest {datasetId, sequence, nonce}
                                   ▼  and switches tab: the first navigation with a payload
InspectTab   Dataset [▾]   Play [ride.mp4 · 300 frames, 41 annotated ▾]   (masks|boxes|both)
   useInspectData(datasetId)
      GET /datasets/{id}/sequences    sequences, complete and in order; classes per frame
      GET /datasets/{id}/images       stored size and boxes per image
   DatasetPlayer
      FrameCanvas (doc 68) with urlFor = the stored file   ← painted from a cache
      StoredOverlay   positives, coloured by class (BoxOverlay + CompositedMasks.rgb)
      useFrameMasks   masks per annotated frame, six ahead, cached
      ◀ Frame  ▶ Play  Frame ▶  [scrub]  12 / 300 · frame 24  [5] fps
```

**A sequence is the whole source.** Autoplay writes no image where nothing was found
(doc 70), so the database alone would play the video with every empty stretch cut out.
The route merges the frames that exist on disk but were never saved back in, unannotated:
- for a video, the extracted files in the dataset's frames directory;
- for a folder, a listing by the same `list_images`, in the same order the Generator used
  to number it.

A folder that has moved plays its annotated frames only.

## Business Rules

1. **An explicit jump wins over what was remembered**, and pressing the button twice jumps
   twice (the `nonce`). Without a jump, the tab opens the remembered dataset, or else the
   first dataset with images.
2. **Tracks:** each sequence, plus "Images not in a sequence" for photos. The Generator's
   jump preselects the run's own video or folder.
3. **Rate:** a video plays at its own fps divided by the median gap between frames, so a
   run kept every 2nd frame of a 10 fps video plays at 5 fps and stays in real time.
   Folders and loose images play at 4 fps. The rate is editable.
4. **Positives only, coloured by class.** Class indices come from the dataset's sorted class
   list, the same list doc 75's timeline uses, so a box and its bar are the same colour.
5. **The picture is painted, not swapped.** This is doc 68's `FrameCanvas`, generalised
   with `urlFor`. An `<img>` swapped on a clock was the bug doc 68 fixed twice.
6. **The jump is disabled while autoplay runs**, because leaving the tab would stop it
   unasked.

## Verified in the running app (2026-09-29)

"Wave 9 video check": 30 frames decoded, 3 annotated by Grounding DINO.

- **"Inspect what I just annotated"** switched to *Inspect datasets* with that dataset open
  at "1 / 30 · frame 0". The stored boxes were drawn in the class colour, with scores.
- **Play ran at 5 fps** (10 fps source, every 2nd frame). The counter read
  2 → 4 → 6 … 17 / 30 over 3 s. Annotated frames showed their boxes, and frames 6–32 read
  "not annotated" with none.
- **The picture changed:** a screenshot at frame 32 showed a different board and pieces
  from frame 0, painted to a 640×640 canvas.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

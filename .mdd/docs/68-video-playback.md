---
id: 68-video-playback
title: Video Playback — Run a Sequence Once, Then Watch It
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [16-inference-engine, 17-image-input-source, 18-multi-head-compose, 53-prescan]
relates: [19-side-by-side-viewer, 49-osdar23-rail, 62-tiled-inference, 67-annotation-view-and-output]
source_files:
  - backend/app/ml/video/decode.py
  - backend/app/ml/video/sequence.py
  - backend/app/ml/video/runner.py
  - backend/app/api/v1/video.py
  - apps/frontend/src/api/video.ts
  - apps/frontend/src/hooks/useSequenceRun.ts
  - apps/frontend/src/components/VideoPlayer.tsx
  - apps/frontend/src/components/SequencePanel.tsx
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
routes:
  - GET /api/v1/video/probe
  - GET /api/v1/video/frame
  - POST /api/v1/video/runs
  - GET /api/v1/video/runs/{job_id}
  - DELETE /api/v1/video/runs/{job_id}
models: []
test_files:
  - backend/tests/test_video_decode.py
  - backend/tests/test_video_sequence.py
  - backend/tests/test_video_api.py
  - apps/frontend/src/api/video.test.ts
  - apps/frontend/src/components/VideoPlayer.test.tsx
data_flow: reads-existing
last_synced: 2026-08-27
status: complete
phase: all
mdd_version: 11
tags: [video, playback, inference-viewer, frame-sequence, prepass, pyav, osdar23]
path: Inference Viewer/Playback
integration_contracts:
  - function: run_heads(...)
    when: every frame of a sequence run
    note: the prepass is N ordinary inference calls, not a second inference path
satisfies_contracts: []
security_read_sites:
  - backend/app/api/v1/video.py — every path is confined by resolve_user_path before decode
known_issues:
  - "The training split is a random shuffle of images (config.py::split_indices). On video that leaks: consecutive frames at 10 Hz are near-duplicates, so a random split puts near-identical frames in train and val and the validation metric becomes a training number. Out of scope here — this doc only plays frames — but making video a first-class input makes the gap easier to walk into. Segment-aware splitting needs its own doc."
---

# 68 — Video Playback

## Purpose

Requested as: *"in the inference tab, we need the option to play images in a folder as
video or use a video format to display and show annotations from the chosen models."*

The viewer already walks a folder with Previous/Next. What it cannot do is show motion,
which is the only way some things are visible at all: a detector that flickers on and off
across consecutive frames looks fine one frame at a time and is obviously broken at 10 Hz.

## The constraint that shapes everything

**A model cannot run at playback speed.** Measured on this machine: Grounded SAM ~5 s per
frame, RF-DETR ~0.1 s, a DINOv2 head ~0.2 s. Ten frames a second is a budget of 100 ms for
everything, and only the smallest model comes close.

So playback and inference are separated in time:

1. **Prepass** — run the chosen models over every frame once, with progress and a cancel.
2. **Play** — step through frames at a chosen rate, drawing overlays from the cache.

That ordering is what makes the result honest. Running live and overlaying whatever has
finished shows annotations *lagging the picture*, which reads as the model being wrong
about where things are rather than as the player being behind.

A prepass is also re-watchable: scrubbing backwards costs nothing, which is exactly what
someone comparing two heads needs.

## How much of it

**The range is chosen before the run, not fixed at "all of it".** This is the same decision
the starter set makes about a gigabyte: a prepass over a 10-minute clip at 30 fps is 18,000
frames, and at Grounded SAM's 5 s per frame that is a day. Nobody wants to discover that by
starting it.

A run takes a **start** and a **count** in frames. The player offers it in seconds, because
that is how anyone thinks about a video, and converts using the probed frame rate — the API
stays in frames, where there is no rounding to argue about.

**The cost is stated before the click**, computed from the frame count, the number of
selected models and their measured per-frame time:

```
120 frames × 2 models ≈ 4 min
```

An estimate, and labelled as one. It is worth more than a spinner precisely because it is
the number that changes the decision — someone who sees four minutes picks a shorter range
instead of cancelling three minutes in.

**A folder is ranged the same way.** 392 tiled OSDaR23 frames is a long wait too, and
"the first 50" is the normal way to check whether a head is worth watching at all.

## Frames, not a stream

A folder of images is already a frame sequence. A video file becomes one by decoding. One
abstraction — `FrameSequence` — so nothing downstream branches on where the pixels came
from, and the same run works on both.

**Decoded on demand, never all at once.** A 300-frame 2464x1600 sequence is ~3.5 GB as raw
RGB. Frames are served one at a time by index and the prepass holds only predictions,
which are small.

**Playback draws frames, not a `<video>` element.** The browser could play an mp4 directly
and it would be smoother — but the frame on screen and the frame the model analysed would
then be a different frame, because `<video>` gives no exact frame index and drops frames
under load. Boxes would visibly trail the object. Drawing frame *N* beside prediction *N*
is the only way an overlay is guaranteed to describe the picture under it.

## Decoding

**PyAV**, because there is no alternative already present: torchvision removed its video
APIs before 0.28 (checked, not assumed), and neither opencv nor imageio is a dependency.
PyAV ships wheels with the ffmpeg libraries bundled, which is what keeps this from becoming
a system-ffmpeg prerequisite the installer cannot satisfy.

It costs installer size. Doc 56 measured the sidecar at 636 MB; PyAV's wheels add roughly
35 MB. Recorded here so the trade is visible rather than discovered at packaging time.

## The prepass is a job, and it is the prescan again

Doc 53 already runs a model over many images with progress, cancellation and polling, and
`PrescanRunner` is the shape this needs. Not reused directly — prescan answers "which images
contain X" and discards the predictions, while this keeps them and asks nothing — but the
job mechanics are the same and are followed rather than reinvented.

**Each frame is an ordinary `run_heads` call.** There is no second inference path: a
sequence run over one frame must produce exactly what the single-image viewer produces for
that frame, or the two surfaces will disagree and only one of them will be believed.

## Path safety

A video path and a folder path both come from the user and both reach the filesystem, so
both go through `resolve_user_path` before anything opens them — the same confinement the
image routes already use. A frame request carries a path *and* an index, and the index is
range-checked against the probe rather than trusted.

## What this does not do

- **No tracking.** Boxes are per frame and identity is not carried across them. A detector
  that finds the same car in 30 frames reports 30 unrelated detections. Tracking is a real
  feature and a separate one.
- **No export.** The run is for looking at. Saving a sequence into a dataset is what the
  Dataset Generator does, and it works frame by frame.
- **No audio.** Nothing here needs it.

## Verified end to end

A 40-frame clip in which a circle moves **12 px per frame**, run through Grounding DINO:

| frame | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 |
|---|---|---|---|---|---|---|---|---|
| box x | 39 | 51 | 63 | 75 | 87 | 99 | 111 | 123 |

Exactly +12 per frame, starting at the true position for frame 0. That is the doc's central
claim measured rather than asserted: if frames and predictions were misaligned by even one,
the boxes would still be 12 apart and the whole series would be shifted.

In the browser, scrubbing 0 → 3 → 6 → 9 moves the box 205 → 256 → 306 → 357 px: 16.9 px per
frame on screen, against 12 in the source at a letterbox scale of 1.408. The overlay is in
the same coordinates as the picture.

## Two modes, chosen rather than inferred

The viewer offers **A single image** and **A video or a folder** as two buttons, the same
shape the Training tab uses. The player used to appear on its own whenever a path happened
to probe as playable, which meant a folder could not be stepped through image by image
without the player also being there — two surfaces for one source, neither of them chosen.

## Why playback did not play

Reported as *"the video is not really playing, more the initial image"*, on a folder.

The clock was fine and the index advanced. What did not happen was **loading**: each frame
was requested only when the clock reached it, a request took ~120 ms, and the frame interval
at 10 fps is 100 ms — so the `<img>`'s `src` was replaced before it had finished decoding,
every time, and the browser went on showing the last frame that *had* decoded. Measured in
the running app: the counter advanced 1, 3, 5, 7, 9, 11 while `img.complete` was `false` on
every single sample.

Two fixes, and both were needed:

**A folder frame is a file, so it is sent as one.** Decoding it with PIL and re-encoding it
as PNG was pure cost: ~120 ms and ~320 KB per frame. `FileResponse` is **~8 ms**, measured.
A video frame still has to be encoded, and goes out as JPEG rather than PNG — the source was
lossy already, so PNG spends two to three times the bytes preserving detail the codec never
recorded.

**Frames are fetched ahead of the clock.** The player preloads the next twelve, which is
what makes this robust rather than merely faster: a video frame is slower than a folder's
file no matter what the encoder does, and a fix that only works when frames are cheap is a
fix that breaks again on the next 4K clip.

Verified after: 26 distinct frames displayed over four seconds, running frame 1 to 38, with
`img.complete` false **zero** times.

## Known Issues

See frontmatter: the training split is not segment-aware, which matters more once video is
a first-class input.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

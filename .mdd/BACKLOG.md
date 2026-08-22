# Backlog — unassigned work

The holding place for work that is agreed as *wanted* but not scoped into a wave. Items
leave here by being written into a wave doc, which is where they get a demo-state, a
feature list and a hash.

**Most of what was here on 2026-08-18 has left.** The seven requested items were planned
into Waves 5, 6 and 7 on 2026-08-19; see the initiative's Waves table. What remains below
is genuinely unassigned.

---

## Unassigned

### Tiled inference

**The largest gap Wave 7.5 left.** Doc 49 tiles images on the way *in* — a 6x4 grid turns a
10.7 px object in a 2464 px frame into 10.1 px at the model's input, which is the difference
between trainable and not. Nothing tiles on the way *out*: a head trained on 472 px tiles
run against a full 2464 px frame finds nothing, and says nothing about why.

What it needs: run the same grid at inference, map each tile's boxes back to frame
coordinates, and merge across the overlap with NMS. `plan_tiles` already produces the grid
and `decode.py` already has class-aware `batched_nms` (doc 43), so the pieces exist.

The open question is **where it lives**. It is not a property of a head — the same head
should be runnable either way — so it is either a per-run option in the viewer and the
Studio, or something a *dataset* records about how it was built so anything trained on it
inherits the setting. The second is more automatic and more surprising.

**Candidate home**: any wave after packaging. It is a correctness gap for far-field data
rather than a blocker for the app's advertised loop.

### Splitting a video dataset by segment

`split_indices` splits by image, which is right for the three reference photo datasets and
**leaks badly on video**. Measured on OSDaR23: consecutive 10 Hz frames differ by 0.4 of
255, and a random split inflated reported mAP by 42% for a trained head.

Doc 49 split by contiguous frame index **by hand**. The app offers no such option, and
nothing warns that a dataset looks like a sequence — even though the signal is usually
sitting in the file names.

Two shapes, and the cheap one may be enough: a **warning** when a dataset's file names carry
consecutive indices, or a real **split-by-segment** option on `TrainingConfig`. The warning
costs almost nothing and turns a silent wrong number into a visible question.

### Live video / webcam input

Deferred out of Wave 3 on 2026-08-18: capture permissions in Tauri, frame pacing and drop
handling were the largest and least-certain chunk of the original draft, and none of it was
needed to prove that wave's payoff.

Wave 3 planning proposed Wave 4 as its home. **That proposal was withdrawn** — Wave 4 is
dataset-generator only. No wave currently claims it.

The groundwork exists and does not need revisiting: doc 17's input contract returns a
single image and a folder as *the same shape*, with items keyed by an opaque `item_id`
rather than a path, precisely so a frame source can satisfy it without the viewer changing.

**Candidate homes**, when someone wants it: Wave 6 (it is another input source for the
Inference Viewer) or after Wave 9 (a webcam in a browser is a different capture path from a
webcam in Tauri, and Wave 9 already forces that split).

### Active-learning hints for review prioritisation

Surface low-confidence or disagreeing predictions first, so a reviewer working a large folder
spends their attention where the model is least sure.

Drafted as an optional Wave 4 feature and **dropped from it on 2026-08-19**: it prioritises
the order of a review loop that has to exist before it can be prioritised, and Wave 4 already
grew to seven features once mask storage needed its own split. Not a rejection — sequencing.

**Candidate home:** any wave after 4, once the generator has been used on a folder big enough
to make ordering matter. The signal it needs — a per-prediction score — is already carried on
`Box.score` and in the Wave 3 `Prediction` payload, so nothing has to be built to keep the
option open.

### Reproducible training runs

Added 2026-08-20, from doc 31's verification. `TrainingConfig.split_seed` makes the
train/val/test **split** deterministic, and deliberately so — doc 11 splits by image to
avoid box-level leakage. Nothing else in the run is seeded: not head weight init, not
batch shuffling, not any augmentation RNG. Two runs of an *identical* config over the
imported blood-cell dataset returned **map 0.4042 and 0.3872** — a 4% relative spread on
inputs that did not change.

That is harmless for a demo and wrong for the thing the Head Trainer actively invites: a
user comparing two configurations, reading a 0.02 difference as signal when run-to-run
noise is larger than that. The saved provenance makes it worse, because a checkpoint
records the config that produced it and implies the number is a property of that config.

**What it needs, roughly:** a `seed` on `TrainingConfig` (distinct from `split_seed`, or
`split_seed` promoted to cover both) threaded through `torch.manual_seed`, the DataLoader
generator and its `worker_init_fn`, then persisted with the run so a checkpoint's metric is
reproducible from its own record. Worth checking whether MPS honours it fully — some
kernels are nondeterministic regardless — in which case the honest fix may be to *report*
the residual variance rather than promise exactness.

**Candidate home:** any wave touching the trainer. Not urgent until someone compares two
runs and believes the difference.

### Depth Anything 3, when it is loadable

Added 2026-08-20, deferred out of Wave 6 the day the wave started. DA3 is the better depth
model and its **Base** variant is Apache-2.0 (V2's Base is CC BY-NC), so it is worth having.
It is not takeable today:

- `config.json` is not a transformers config — no `architectures`, no `model_type`, just a
  custom `__object__` pointing at `depth_anything_3.model.da3.DepthAnything3Net`.
- The `depth-anything-3` package requires **`numpy<2`**; this environment runs numpy 2.5.2
  under torch 2.13. It also pulls `open3d`, `evo`, `e3nn`, a pinned `moviepy==1.0.3` and a
  second `fastapi`.

Wave 6 shipped **Depth Anything V2 Small** (95 MB, Apache-2.0, transformers-native) instead,
on the same reasoning that chose SAM 3 over SAM 3.1.

**Revisit when** `transformers` gains a DA3 architecture — at which point it is a catalogue
entry plus a `build_foundation` case and nothing else, because doc 36 put the contract in
place. The hand-written-loader alternative was considered and rejected: reimplementing
`DepthAnything3Net` against a bespoke config format forks from upstream on every release.

### Ultralytics-derived detectors — an AGPL decision, not a technical one

Added 2026-08-20 while scoping Wave 7.5. Jan proposed YOLOv11/v12 and
`Sompote/DINOV3-YOLOV12`. Both are technically fine and both are **AGPL-3.0**, inherited
from Ultralytics (confirmed on PyPI: `ultralytics` is AGPL-3.0).

That is a strong copyleft licence. This project is billed as a sharable, installable desktop
app, so distributing it with AGPL code linked in obliges releasing **the whole app** under
AGPL. That is a decision to take deliberately, and **Wave 8 (Packaging) is where it belongs**
— doc 35's licence surfacing exists so exactly this is not discovered during packaging.

Also noted: `itsprakhar/Yolo-DinoV2` ships **no pretrained weights** ("Pretrained weights are
not available"), so it could not have provided a default detector regardless of licence.

**If the answer is no**, the Apache-2.0 substitutes are already in `transformers`:
**RF-DETR** (taken in Wave 7.5) and **RT-DETRv2** (`PekingU/rtdetr_v2_r18vd`).

### Depth Anything 3, when it is loadable

Wave 4 brings SAM 3 in for the **Dataset Generator**, where reviewing masks is the point.
Using it in the *Annotation Studio* needs a mask-drawing and refining tool that does not
exist — the same gap Wave 5 hits for segmentation heads, and the reason Wave 6 puts Depth
Anything 3 in the viewer rather than the Studio.

Listed in Wave 6's Open Research as a candidate, deliberately not assumed.

---

## Where the seven items went

| Item | Wave | Note |
|---|---|---|
| #1 trained backbone+head as annotation model | **5** | The flywheel. Note Wave 4 already runs expert heads over images to *generate datasets*; Wave 5 is the interactive Studio version. |
| #2 choose model/head upfront in Inference Viewer | **5** | ⚠️ May be largely shipped — Wave 3's `HeadRunPanel` already does much of this. Scope against what exists. |
| #3 drag-and-drop images | **7** | Feeds doc 17's contract under Tauri; the browser case has no path and needs a decision. |
| #4 prompt guidance in the Annotation Studio | **7** | Must cover *which* prompting mode the user is in, since by then there are three. |
| #5 intro tab, "for dummies" | **7** | Written after 5 and 6, or it documents an app that changed. |
| #6 SAM 3 + Depth Anything 3 | **4** and **6** | SAM 3 stayed in Wave 4 (it is what makes segmentation trainable — dataset-generator work) and was upgraded from plain SAM. Depth Anything 3 is Wave 6, Inference Viewer first. |
| #7 SigLIP 2 / Gemini Flash | **dropped** | See below. |

### #7 — dropped 2026-08-19, with reasons

Recorded so it is not re-proposed from scratch.

- **SigLIP 2** is an image–text embedding model. It scores how well an image matches text
  and does **not** localise, so it produces no boxes and is not a Grounding DINO
  alternative. It could have served as an alternative *backbone*, as zero-shot
  classification, or as a verifier re-ranking another detector's proposals — three
  different features, none of them "swap out the detector". Dropped rather than scoped.
- **Gemini Flash Vision** is API-only; there are no local weights. It would send the user's
  own image folders off their machine, contradicting the premise the app is built on, and
  adds key handling, per-call cost, rate limits and offline failure. If a cloud VLM is ever
  wanted, Wave 9 is where the user has already accepted cloud compute — labelled, and never
  a default.
- For "better semantics than Grounding DINO while staying local", **SAM 3** is the stronger
  bet and is already in Wave 4.

---

## To verify at planning time

- Per-variant licences for Depth Anything 3, and the full Meta SAM License text. Both are
  Wave 8 packaging constraints and both are decided in the waves that introduce them.
- ~~Whether SAM 3.1 supersedes SAM 3 for this use.~~ **Answered 2026-08-19: no.** SAM 3.1
  (2026-03-27) adds only Object Multiplex — ~2× *video* throughput — and has **no HuggingFace
  `transformers` integration**, unlike `facebook/sam3` which ships `Sam3Processor`/`Sam3Model`.
  Taking 3.1 would add a second model-loading path for a benefit no current wave uses.
  Reconsider only if video is picked up. Recorded in the Wave 4 doc.
- Exact model sizes, so the admin panel's disk warnings stay honest (~14 GB free here).
  **SAM 3 measured 2026-08-19: ~0.9B params, F32 ≈ 3.6 GB**, and the repo is *gated* —
  per-repo access approval on top of a token, which DINOv3 does not require.
- Whether #2 asks for anything `HeadRunPanel` does not already do.

# Backlog — unassigned work

The holding place for work that is agreed as *wanted* but not scoped into a wave. Items
leave here by being written into a wave doc, which is where they get a demo-state, a
feature list and a hash.

**Most of what was here on 2026-08-18 has left.** The seven requested items were planned
into Waves 5, 6 and 7 on 2026-08-19; see the initiative's Waves table. What remains below
is genuinely unassigned.

---

## Unassigned

### Private Network Access — does a hosted GUI reach a local backend?

Added 2026-08-25 from a design question: serve the SPA from a small central server while
every user runs the frozen sidecar on their own machine, so the GUI is shared and the
processing, the images and the model cache stay local. The frontend already supports it —
`API_BASE_URL` reads `VITE_DINO_API_URL` and its comment already anticipates a build "where
the backend is not on loopback" — and Wave 8's PyInstaller sidecar is already the local
agent that architecture needs.

**The unknown is browser policy, and it should be spiked before anything is designed around
it.** Loopback is a "potentially trustworthy" origin so HTTPS→`http://127.0.0.1` is not
mixed content, but Chrome's Private Network Access treats a public page calling a local
address as a private-network request and wants
`Access-Control-Allow-Private-Network: true` on the preflight. Safari and Firefox differ.
One static page served from a non-localhost origin answers this in an afternoon.

**If it works**, the rest is small: make `_ALLOWED_ORIGINS` configurable rather than the
hardcoded tuple in `main.py`, add the PNA header, add a directory-browsing endpoint to
replace the native picker, and add a static build target.

**The security constraint is the part not to get wrong.** `read_image` opens any path it is
given, with no confinement — correct for a desktop app where the user owns both ends, and
dangerous the moment a web origin can call it. A wildcard allowlist would let any site the
user visits read images off their disk and enumerate folders through `/annotate/folder`.
`main.py` already states the stake: *"Not `*` — this process holds an HF token and local
filesystem reach."* A hosted GUI wants a strict single-origin allowlist **and** a per-session
token the local binary prints and the user pastes in.

**Relationship to Wave 9**: adjacent, not the same. Wave 9 assumes hyperscaler compute and
shared storage; this assumes neither and shares nothing but the GUI. Worth deciding which
of the two "a server" is meant to mean before Wave 9 is planned.

### Code signing and notarization

Deferred out of Wave 8 on 2026-08-21 because it needs certificates: an Apple Developer ID
for macOS notarization and a code-signing certificate for Windows. Neither can be held or
used by an assistant, so this is Jan's whichever way it is scheduled.

**Until it exists**, the macOS build is Gatekeeper-blocked on first launch (right-click →
Open is the workaround, which is not a thing to tell users) and Windows shows a SmartScreen
warning. `release.yml` already publishes a **draft** rather than a live release, so an
unsigned build cannot reach anyone by accident — that guard should stay until signing lands.

Tauri handles both through `bundle.macOS.signingIdentity` and `bundle.windows.certificateThumbprint`,
with secrets supplied by the release job. The work is mostly obtaining and storing the
certificates rather than wiring them.

### Auto-update

Deferred out of Wave 8 on 2026-08-21. Depends on signing: an updater that installs unsigned
payloads is worse than no updater.

It also needs a real answer to **size**. The installers are 181–377 MB and Tauri's updater
does not diff — it replaces the whole app. Shipping that for a one-line fix is a bad citizen,
and the honest options are either updating the *sidecar* separately from the shell (they
change at very different rates) or accepting full downloads and releasing rarely.

### First-run experience on a clean machine

Deferred out of Wave 8 on 2026-08-21, and the smallest of the three — but the one nobody has
tested. **No installer has ever been installed.** The macOS `.app` was launched from its own
build directory on the machine that built it, which shares that machine's model cache and
data directory.

What is unverified: that a fresh install finds no cache and says so usefully, that the Admin
tab is discoverable enough to be the first stop, and that the sidecar starts when nothing
else about the machine is set up. Doc 38's intro tab and doc 02's download manager are the
pieces; whether they add up to a first run has not been seen.

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

### Mask refinement in the Annotation Studio

**Retitled 2026-08-25.** This entry carried the heading "Depth Anything 3, when it is
loadable" twice over, which was a copy-paste error: its body was always about SAM 3 in the
Studio and never about depth.

**Mostly delivered by doc 61** on 2026-08-25. The Studio now shows a concept segmenter's
masks and stores them as COCO RLE, so the original framing — "using it in the Annotation
Studio needs a mask-drawing and refining tool that does not exist" — turned out to be
answering the wrong question. Doc 45 declined mask review in the Studio because there was
no mask *editor*; doc 61 observed that showing and keeping a mask the pipeline had already
computed was never the same question, and reversed it on the record.

**What genuinely remains** is the editor: a mask cannot be reshaped, and a hand-drawn box
never gains one. A reviewer can accept, reject or remove a mask, not correct it. Brush and
box-prompt-to-SAM are the two obvious shapes — the second is nearly free, since SAM 2.1 is
already loaded and box-prompted segmentation is exactly what it does.

### ~~Segmentation-head training has no data path~~ — delivered 2026-08-25

**Done.** A `linear-segmenter` now trains on stored masks: verified end to end on
Vegetation_track with `class_names ["background", "signal", "train tracks"]`, loss falling
3.16 → 1.70 and mIoU rising 0.095 → 0.263 across three epochs. Two images, so the number is
meaningless as a model — but loss falling and mIoU rising monotonically only happens if the
targets are genuinely aligned with the images.

Four decisions worth keeping:

* **Class 0 is background, and only for segmentation.** Every pixel belongs to something and
  most belong to none of the annotated classes; without it the loss can only ignore them and
  the model learns to label the whole frame. `classes_for_task` is where that lives. Index 0
  is not merely convention: the overlay registry already treats `class_names[0] ===
  'background'` as the signal to draw class 0 transparent, so a head trained here renders
  correctly in the Viewer with nothing told about it.
* **`unclear` paints last, over positives.** The reviewer's doubt is about that region, and
  resolving it in the model's favour is the one thing they did not say.
* **An unsegmented image is not an empty one.** A box-annotated image in a mixed dataset is
  one nobody looked at with a segmenter; training on it teaches that whatever is in it is
  background. An image whose masks were all *rejected* is genuine background supervision —
  which is why rejecting stores a `negative` rather than deleting. `TrainingSample.segmented`
  is what tells them apart.
* **Targets go through the `GeometryTransform`, never the plan.** `transform_mask` was
  written for this in doc 10 and had sat unused ever since; it took a `PreprocessPlan`, and
  was retargeted to match `transform_boxes` so a mask and a box on one image cannot disagree
  about what happened to it.

**What the real run caught that the unit tests did not**: the target needs a leading batch
dimension, like every other target in the module. The first version of the tests added it
themselves before calling the loss, so they passed while a run failed with "Expected input
batch_size (1) to match target batch_size (448)". The test now passes `build_targets`
output untouched, exactly as `run_epoch` does.

**Also fixed, same day**: the vocabulary is built per task rather than unioned. Boxes and
masks supervise different heads, so `build_class_vocabulary` and `build_mask_vocabulary` are
separate and a `SampleSet` carries both. A segmenter never sees a box-only class and a
detector never sees a mask-only one.

This was not the cosmetic fix it looked like. On Vegetation_track the union had put `signal`
— a leftover box class, on no mask — into a segmentation head, and removing it took epoch-1
train loss from **3.16 to 0.70** and best mIoU from **0.263 to 0.539**. A channel that never
appears in any target still takes probability mass.

It also needed the run guard to become task-aware. `classes_for_task` returns
`("background",)` for a dataset with no masks at all, so a guard counting that list sees one
class and lets the run proceed to train on nothing; `learnable_classes` answers the question
the guard actually means.

---

### (original entry, kept for the reasoning)

Added 2026-08-25, found while answering a question about the ADE20k head rather than by an
audit. `linear-segmenter` is registered `trainable=True` with `target_format="masks"`, and
both `segmentation_loss` and `segmentation_metrics` are wired to it — but nothing produces
the target it reads. `build_samples` reads only `store.image_annotations` (boxes),
`TrainingSample` has no mask field, and `build_targets` branches on `classification` and
falls through to detection with no segmentation case. `segmentation_loss` reads
`targets["mask"]`, so a run raises `KeyError: 'mask'` on the first batch. Nothing refuses it
earlier.

Its own description still says *"Needs a dataset with masks — the Annotation Studio produces
boxes until SAM lands."* SAM landed; doc 61 stores masks per image.

**Three contained pieces**: carry masks through `build_samples` into `TrainingSample`, add a
segmentation branch to `build_targets` that rasterises the RLE through the same
`GeometryTransform` the image took, and correct the description. The head, the loss and the
metrics all already exist.

**Why it is worth doing**: it is the difference between the ADE20k head — someone else's
150 fixed classes — and a segmenter trained on the user's own. It is also the natural
consumer of the masks doc 61 started storing.

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
- Whether Meta published a fine-tuning recipe for SAM 3, and whether the SAM License permits
  distributing a derivative. Asked 2026-08-25 and not answered. Largely moot while Grounded
  SAM's halves are Apache-2.0: Grounding DINO is the fine-tunable half worth the effort, and
  `boxes.prompt` already stores exactly the box+phrase pairs its training needs.
- Exact model sizes, so the admin panel's disk warnings stay honest (~14 GB free here).
  **SAM 3 measured 2026-08-19: ~0.9B params, F32 ≈ 3.6 GB**, and the repo is *gated* —
  per-repo access approval on top of a token, which DINOv3 does not require.
- Whether #2 asks for anything `HeadRunPanel` does not already do.

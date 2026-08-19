---
id: dinotraining-wave-4
title: "Wave 4: Dataset Generator (SAM 3 + Expert-Head Auto-Annotation)"
initiative: dinotraining
initiative_version: 7
status: planned
depends_on: dinotraining-wave-3
demo_state: "User runs trained expert head(s) over new images, reviews/marks predictions, and saves a new dataset ready to train another head. Separately, SAM 3 proposes segmentation masks over an image set which the user reviews and saves — closing the gap that made segmentation untrainable in-app."
created: 2026-08-14
hash: bb60dd7b
---

# Wave 4: Dataset Generator (SAM 3 + Expert-Head Auto-Annotation)

## Demo-State

In the **Dataset Generator** tab the user selects a backbone + one or more trained expert
heads and points them at a new image set. Predictions are shown with the same review UX as
the Annotation Studio (mark **positive / negative / unclear**, adjust or add boxes by hand),
and the reviewed results are saved back into the dataset store in the training format — ready
to train the next head. This closes the annotate→train→generate data flywheel.

This wave also brings **SAM 3 (Segment Anything with Concepts)** in as a second foundation
annotator alongside Grounding DINO: a text concept proposes segmentation masks the user
reviews and saves as training targets. That is what finally makes the segmentation head
trainable in-app — until this wave lands, segmentation trains only on user-brought mask
datasets.
*(Not complete until this can be manually demonstrated.)*

## Blocked on Jan

**`facebook/sam3` is a gated HuggingFace repo.** Meta requires accepting the SAM License and
sharing contact information before the weights can be downloaded. This is the same shape as
DINOv3 — `HF_TOKEN` plus a per-model licence link — but it means **features 4 and 6 cannot be
demonstrated until access is granted on Jan's HuggingFace account**. Request it early; the
box half of the wave (features 1, 3, 5, 7) is unblocked and can ship first.

Weights are ~0.9B parameters in F32 (**≈3.6 GB**) against ~14 GB free on the home volume.
Not blocking, but it is the largest single download the project has asked for.

## Open questions waived for this wave

The initiative carries two unchecked open product questions. Both are **deliberately waived
here, not answered** — exactly as Wave 3 did:

- `[ ] Code-signing / notarization for macOS + Windows installers` — **Wave 8**
- `[ ] Which hyperscaler(s) to support first for the website` — **Wave 9**

Neither can influence a dataset generator. Answering "which hyperscaler" merely to clear the
gate would turn a guess into an architectural commitment nobody has made.

## Decisions taken during planning (2026-08-19)

**SAM 3, not SAM 3.1.** SAM 3.1 shipped 2026-03-27 as a drop-in replacement, but its only
addition is Object Multiplex — roughly 2× throughput for **video** tracking, which this wave
does not use — and it has **no HuggingFace `transformers` integration**, requiring the
`facebookresearch/sam3` GitHub package instead. `facebook/sam3` exposes `Sam3Processor` /
`Sam3Model`, so it drops into the existing `AutoModel`-based model manager. Taking 3.1 would
mean a second model-loading path for a benefit this wave cannot use. Revisit if and when
video lands (it is unassigned in `.mdd/BACKLOG.md`).

**Mask review is verdict-only** — accept / reject / unclear per mask, no pixel editing. SAM 3
masks are good enough that a verdict is usually sufficient to make segmentation trainable,
and this is the smallest change to the Wave 1 review surface. A brush or polygon editor is a
later wave; it is not required to close the flywheel.

**Masks are stored as COCO RLE.** It is compact, lossless over SAM's ragged borders, handles
holes, and is exactly what the COCO `segmentation` field expects — so `03-dataset-store`'s
export path extends rather than forks. The trade-off accepted: RLE is not hand-editable
without decoding, which is fine given verdict-only review, and is the constraint to revisit
first if mask editing is ever added.

**`active-learning-hints` is dropped to `.mdd/BACKLOG.md`.** It prioritises review order in a
loop that must exist before it can be prioritised, and this wave already grew to seven
features. Not a rejection — a sequencing call.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | mask-dataset-store | — | planned | — |
| 2 | sam3-model-entry | — | planned | — |
| 3 | expert-annotator | — | planned | — |
| 4 | sam-mask-annotator | — | planned | mask-dataset-store, sam3-model-entry |
| 5 | generator-review-ui | — | planned | expert-annotator |
| 6 | mask-review-ui | — | planned | sam-mask-annotator, generator-review-ui |
| 7 | generated-dataset-writer | — | planned | mask-dataset-store, generator-review-ui, mask-review-ui |

Features 1–3 are independent and can be built in any order; 1 and 2 are pure backend and are
the safest place to start. The box path (1, 3, 5, 7) is demonstrable without SAM 3 access.

### Feature notes

**1. mask-dataset-store** — extend `03-dataset-store` with masks. A new `masks` table keyed to
`images`, RLE stored alongside the box rows, manifest `version: 2`, and the COCO exporter
emitting `segmentation`. `Provenance` grows from `["grounding-dino", "hand-drawn"]` to include
`expert-head` and `sam3`. `DatasetCounts` gains a mask tally so the Wave 1 `CounterBar`
reports both.
⚠️ `backend/app/datasets/store.py` is at **286 lines** — the 300-line hook will block this.
The mask write path is a **new sibling module**, not an addition to `store.py`. Split first,
then build. The same applies to `models.py` if the mask types push it over.

**2. sam3-model-entry** — SAM 3 in the model registry and manager as a **gated family beside
`dinov3`**: `repo_id="facebook/sam3"`, family `sam3`, licence surfaced as Meta's custom *SAM
License* with a link, marked unavailable without a token, download / remove / cache-size via
the existing admin tab. No new download machinery — reuse the gated path Wave 1 built.
⚠️ `backend/app/ml/registry.py` is at **293 lines**. Split before adding the entry.

**3. expert-annotator** — run an installed head instance over an image set through the Wave 3
inference engine and turn each `Prediction` into proposed annotations. **No coordinate
conversion is needed**: `app/ml/inference/results.py` already defines its `Box` as xywh in
absolute source pixels, top-left origin, explicitly so this wave could consume it directly.
Boxes arrive with `provenance="expert-head"` and the head's score. Backend only; refuses
heads whose `render_hint` is not `boxes` with a reason the UI can display.

**4. sam-mask-annotator** — SAM 3 as the second foundation annotator. Concept-prompted: a text
noun phrase returns masks **and** boxes. Also accepts existing Grounding DINO boxes as
prompts, so a Wave 1 box dataset can be lifted into masks rather than re-annotated from
scratch. Returns RLE for storage; dense preview travels as base64 PNG per the Wave 3 rule
(`mask_png`, never nested JSON).

**5. generator-review-ui** — the Dataset Generator tab, currently an 8-line stub
(`apps/frontend/src/tabs/DatasetGeneratorTab.tsx`). Image-source picker + annotator picker +
box review, reusing `AnnotationCanvas`, `CounterBar` and `ImageSourcePicker`. The head picker
must be the **same head-instance descriptor contract** Wave 3's `HeadRunPanel` uses — listing
task, provenance kind, datasets, classes and metrics, never a filename. If that means
promoting `HeadRunPanel` to a shared component, do that rather than copying it; the handoff
already flags a third consumer as the trigger for promotion.

**6. mask-review-ui** — mask overlay plus per-mask accept / reject / unclear, using the same
three verdicts as boxes so the dataset store stays one format.
⚠️ `AnnotationCanvas.tsx` is at **264 lines**. This is a **sibling component**, not an
extension of it. Reuse `components/overlays/` — the `OVERLAY_RENDERERS` record is already
keyed by `RenderHint`, so the mask renderer exists; a `task ===` comparison here is a defect.

**7. generated-dataset-writer** — write reviewed boxes and masks into a dataset through the
feature-1 store, tagged with **what produced them**: the head instance id and its provenance
summary, or `sam3` plus the concept prompt. This is what makes generated data traceable back
to the model that generated it, and it is the contract the Wave 2 trainer reads when the next
head is trained on this output.

## Open Research

- **Does a `negative` verdict mean anything for a segmentation target?** A rejected box is a
  hard negative; a rejected mask is more likely just "not a target". Decide before feature 6
  whether rejected masks are stored at all, or only counted.
- **How far dataset versioning goes.** Feature 7 records the producing model per annotation.
  Whether a generated dataset also needs a parent-dataset link and a generation timestamp —
  i.e. a lineage chain — is unresolved and affects the manifest `version: 2` schema, so settle
  it during feature 1 rather than after.
- **SAM 3 gated-access UX.** DINOv3 shows "unavailable without a token" plus a licence link.
  SAM 3 additionally requires *per-repo access approval*, which a token alone does not grant —
  a 403 with a valid token must read as "request access at this URL", not "bad token".

## Explicitly not in scope

- **Mask editing** (brush or polygon). Verdict-only — see the decisions above.
- **Active-learning / confidence-ordered review.** Moved to `.mdd/BACKLOG.md`.
- **Live video / webcam.** Withdrawn from this wave on 2026-08-18; unassigned in the backlog.
- **Depth Anything 3.** Wave 6, in the Inference Viewer, where no new labelling tool is needed.
- **Training a segmentation head on the generated masks.** Wave 2 already trains segmentation;
  this wave supplies the targets it was missing. Confirm the format round-trips, but the
  training run itself is not a Wave 4 feature.

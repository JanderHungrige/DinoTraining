---
id: dinotraining-wave-4
title: "Wave 4: Dataset Generator (SAM 3 + Expert-Head Auto-Annotation)"
initiative: dinotraining
initiative_version: 7
status: complete
depends_on: dinotraining-wave-3
demo_state: "User runs trained expert head(s) over new images, reviews/marks predictions, and saves a new dataset ready to train another head. Separately, SAM 3 proposes segmentation masks over an image set which the user reviews and saves — closing the gap that made segmentation untrainable in-app."
created: 2026-08-14
hash: 93ffe075
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

### Both halves demonstrated — marked complete 2026-08-20

**Mask half** (2026-08-19): Grounded SAM — concept in, masks out, reviewed, saved, exported
to COCO — against real Grounding DINO + SAM 2.1 on MPS. Better than written, in fact: it
needs no gated model at all. SAM 3 verified the same day against real weights.

**Expert-head half** (2026-08-20): held up not by a defect but by there being **no
pretrained detection head in existence** to install — DINOv2 publishes classification,
segmentation and depth only. The unblock was therefore to *train* one, which needed a box
dataset the app could not yet accept. `31-external-dataset-import` closed that gap, and
three detectors were trained on ungated HuggingFace datasets over frozen `dinov2-small`:

| dataset | images | classes | map | map_50 |
|---|---|---|---|---|
| thermal-dogs-and-people | 203 | 2 | 0.404 | 0.590 |
| blood-cell-object-detection | 364 | 3 | 0.387 | 0.610 |
| chess-pieces | 289 | 13 | 0.525 | 0.748 |

Demonstrated in the browser end to end: Dataset Generator → "A head you trained" → thermal
head → propose → 20 boxes over the two people in a held-out thermal frame → save → 20 rows
stored as `expert-head` / `person`, each carrying a producer snapshot naming the head
instance. Running it also surfaced two defects in code this wave depends on — the missing
NMS (doc 16) and generated boxes losing their class (doc 29) — both fixed and pinned.

`31-external-dataset-import` is a **tenth doc for this wave**, built after the other nine.

## Nothing is blocked (revised 2026-08-19)

An earlier version of this plan had features 4 and 6 blocked on Meta granting access to the
gated `facebook/sam3` repo. **That block is gone.** Measured, not assumed:

| Model | Prompt | Returns | Gated | Licence | Weights |
|---|---|---|---|---|---|
| `facebook/sam3` | text concept | masks + boxes | **yes, manual approval** | SAM License | **3.44 GB** |
| `facebook/sam2.1-hiera-small` | points/boxes | masks | no | Apache-2.0 | **184 MB** |
| `facebook/sam2.1-hiera-tiny` | points/boxes | masks | no | Apache-2.0 | 156 MB |
| `facebook/sam-vit-base` | points/boxes | masks | no | Apache-2.0 | 375 MB |

No ungated model is a drop-in for SAM 3: SAM 1 and SAM 2.1 are *visually* prompted, take no
text and return no boxes. But **Grounding DINO + SAM 2.1 composed reproduces SAM 3's exact
contract** — a text concept in, masks and boxes out. Grounding DINO is already installed and
ungated, so the whole wave is buildable and verifiable today for a 184 MB Apache-2.0
download and no gated access whatsoever.

`transformers` 5.15.0 already exposes `SamModel`, `Sam2Model` **and** `Sam3Model`, so neither
path needs dependency work.

**We never download SAM 3.** It is offered in the admin tab and the *user* triggers it, after
supplying their own token and acknowledging the licence (feature 3). Nothing in this wave
requires SAM 3 weights to be present to be complete.

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

**Grounded SAM is a permanent first-class annotator, not a test scaffold.** Most users of an
installable desktop app will not want to accept Meta's custom licence or wait on manual
approval, so an Apache-2.0 segmentation path that needs no gating at all is a product
feature rather than scaffolding. It also keeps this wave verifiable forever instead of only
until SAM 3 arrives.

**One `MaskAnnotator` interface, two implementations keyed by id** — `grounded-sam` and
`sam3` — following the project's registry rule. This is what makes SAM 3 a drop-in addition
later rather than a rewrite, and it is why the review UI never learns which annotator
produced a mask.

**The ungated path uses `facebook/sam2.1-hiera-small`** (184 MB, Apache-2.0). Newest
architecture, small enough to matter against ~15 GB free, and swappable via the registry.

**The user supplies their own HF token through the app.** A field in the admin tab writes
`HF_TOKEN` to `.env`, alongside an explicit acknowledgement that they have read Meta's SAM
License. Since the app deliberately does not download gated weights on the user's behalf,
the obligation is made visible rather than implied — and Wave 8 packaging needs that record.

**`active-learning-hints` is dropped to `.mdd/BACKLOG.md`.** It prioritises review order in a
loop that must exist before it can be prioritised, and this wave already grew to seven
features. Not a rejection — a sequencing call.

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | mask-dataset-store | [22](../docs/22-mask-dataset-store.md) | complete | — |
| 2 | mask-annotator-registry | [23](../docs/23-mask-annotator-registry.md) | complete | — |
| 3 | hf-token-settings | [24](../docs/24-hf-token-settings.md) | complete | — |
| 4 | expert-annotator | [25](../docs/25-expert-annotator.md) | complete | — |
| 5 | generator-review-ui | [26](../docs/26-generator-review-ui.md) | complete | expert-annotator |
| 6 | grounded-sam-annotator | [27](../docs/27-grounded-sam-annotator.md) | complete | mask-dataset-store, mask-annotator-registry |
| 7 | mask-review-ui | [28](../docs/28-mask-review-ui.md) | complete | grounded-sam-annotator, generator-review-ui |
| 8 | generated-dataset-writer | [29](../docs/29-generated-dataset-writer.md) | complete | mask-dataset-store, generator-review-ui |
| 9 | sam3-annotator | [30](../docs/30-sam3-annotator.md) | complete | mask-annotator-registry, hf-token-settings |

**Build order: 1 ✅ → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9.**

Revised 2026-08-19 after the gating research above. The wave grew from seven features to
nine: `sam3-model-entry` split into `mask-annotator-registry` (the interface plus both
catalogue entries) and `sam3-annotator` (the gated implementation), and `hf-token-settings`
was added because the user supplies their own token through the app. It is a large wave, but
the added features are small and the split is what removes the external block.

`sam3-annotator` is deliberately **last**: it is the only feature whose real-weights
verification depends on a download we do not perform. Its code and unit tests do not — it is
written against the same interface feature 6 already proved, and stubbed for tests.

### Feature notes

**2. mask-annotator-registry** — one `MaskAnnotator` contract: a text concept and an image in,
masks-plus-boxes out. Two catalogue entries keyed by id, `grounded-sam` and `sam3`, each
declaring its model requirements, licence, whether it is gated, and its download size. Model
registry entries for `facebook/sam2.1-hiera-small` and `facebook/sam3` land here too. No
`if annotator == "sam3"` anywhere downstream — that is a defect, exactly as `task ===` is in
`components/overlays/`.
✅ **Correction (2026-08-19):** an earlier draft warned that `backend/app/ml/registry.py`
was at 293 lines and needed splitting. It is at **115** and has room. The 293-line file is
`backend/app/ml/heads/registry.py` — the *head* registry, which this feature does not
touch. The handoff named "registry.py" without a path and the ambiguity propagated.

**3. hf-token-settings** — a field in the admin tab where the user pastes their own
HuggingFace token, plus an explicit checkbox acknowledging Meta's SAM License with a link to
it. Writes `HF_TOKEN` to `.env` and records the acknowledgement.
- **The token is never returned, never logged, and never rendered back.** The read endpoint
  reports only `configured: true|false` and a masked hint (last 4 characters at most).
- `.env` is written with `0600` permissions and is already gitignored.
- `get_settings` is `lru_cache`d, so the cache must be cleared after a write or the new token
  is invisible until restart — and uvicorn does not reload.
- Explanation text must state plainly: what the token is for, that the app never downloads
  gated weights on the user's behalf, that SAM 3 needs *manual approval* on top of a token,
  and that Grounded SAM needs neither.

**4. expert-annotator** — run an installed head instance over an image set through the Wave 3
inference engine and turn each `Prediction` into proposed annotations. **No coordinate
conversion is needed**: `app/ml/inference/results.py` already defines its `Box` as xywh in
absolute source pixels, top-left origin, explicitly so this wave could consume it directly.
Boxes arrive with `provenance="expert-head"` and the head's score. Backend only; refuses
heads whose `render_hint` is not `boxes` with a reason the UI can display.

**5. generator-review-ui** — the Dataset Generator tab, currently an 8-line stub
(`apps/frontend/src/tabs/DatasetGeneratorTab.tsx`). Image-source picker + annotator picker +
box review, reusing `AnnotationCanvas`, `CounterBar` and `ImageSourcePicker`. The head picker
must be the **same head-instance descriptor contract** Wave 3's `HeadRunPanel` uses — listing
task, provenance kind, datasets, classes and metrics, never a filename. If that means
promoting `HeadRunPanel` to a shared component, do that rather than copying it; the handoff
already flags a third consumer as the trigger for promotion.

**6. grounded-sam-annotator** — the ungated implementation of the feature-2 contract, and the
one that proves the pipeline end to end. A text concept goes to Grounding DINO, whose boxes
become SAM 2.1 box prompts, and the masks come back as RLE for storage with the originating
boxes alongside. This is also exactly the "lift an existing Wave 1 box dataset into masks"
path, since the box source is pluggable. Dense preview travels as base64 PNG per the Wave 3
rule (`mask_png`, never nested JSON); RLE is what is stored.

**7. mask-review-ui** — mask overlay plus per-mask accept / reject / unclear, using the same
three verdicts as boxes so the dataset store stays one format.
⚠️ `AnnotationCanvas.tsx` is at **264 lines**. This is a **sibling component**, not an
extension of it. Reuse `components/overlays/` — the `OVERLAY_RENDERERS` record is already
keyed by `RenderHint`, so the mask renderer exists; a `task ===` comparison here is a defect.

**8. generated-dataset-writer** — write reviewed boxes and masks into a dataset through the
feature-1 store, tagged with **what produced them**: the head instance id and its provenance
summary, or the annotator id plus the concept prompt. This is what makes generated data
traceable back to the model that generated it, and it is the contract the Wave 2 trainer
reads when the next head is trained on this output.

**9. sam3-annotator** — the gated implementation of the same feature-2 contract, using
`Sam3Model`/`Sam3Processor` and SAM 3's native concept prompting (no Grounding DINO stage).
Selected by id; nothing downstream changes. **We do not download the weights** — the admin
tab offers it and the user triggers it once they have a token and approval.
- A **403 with a valid token means "request access at this URL", not "bad token"**, and must
  say so. This is the one failure mode DINOv3 does not have.
- Unit-testable with a stubbed model; real-weights verification waits on the user's download
  and is recorded as such rather than silently skipped.

## Open Research

- **Does a `negative` verdict mean anything for a segmentation target?** A rejected box is a
  hard negative; a rejected mask is more likely just "not a target". Decide before feature 6
  whether rejected masks are stored at all, or only counted.
- ~~**How far dataset versioning goes.**~~ **Answered 2026-08-19 in feature 8, later than
  this item asked for.** Per-annotation provenance: a `producer` JSON snapshot on `boxes`
  and `masks` (migration v5). Chosen over per-dataset lineage because a dataset can mix
  producers, and because a snapshot outlives a deleted head. Dataset lineage — parent link
  and generation timestamp — was considered and deliberately not built; it only earns its
  keep once datasets are routinely generated from other datasets. Recorded in doc 29.
- **Does Grounded SAM need its own provenance value?** The store currently records `sam3`.
  A mask produced by Grounding DINO + SAM 2.1 is not from SAM 3, so either the value widens
  to `grounded-sam` (another migration — cheap now that the runner exists) or provenance
  records the *class* of producer and the annotator id lives beside it. Settle in feature 2,
  before feature 6 writes any masks.

## Explicitly not in scope

- **Mask editing** (brush or polygon). Verdict-only — see the decisions above.
- **Active-learning / confidence-ordered review.** Moved to `.mdd/BACKLOG.md`.
- **Live video / webcam.** Withdrawn from this wave on 2026-08-18; unassigned in the backlog.
- **Depth Anything 3.** Wave 6, in the Inference Viewer, where no new labelling tool is needed.
- **Training a segmentation head on the generated masks.** Wave 2 already trains segmentation;
  this wave supplies the targets it was missing. Confirm the format round-trips, but the
  training run itself is not a Wave 4 feature.

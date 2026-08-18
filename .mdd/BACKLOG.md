# Backlog — candidate work after Wave 4

Not a plan. This is the holding place for work that is agreed as *wanted* but not yet
scoped into a wave. Items move out of here through `/mdd plan-wave`, which is where they
get a demo-state, a feature list and a hash.

**Wave 4 (Dataset Generator) is explicitly scoped to the dataset generator only.** Nothing
in this file belongs in it.

---

## Deferred from Wave 3

### Live video / webcam input

Deferred out of Wave 3 on 2026-08-18. Capture permissions in Tauri, frame pacing and drop
handling were the largest and least-certain chunk of the original draft, and none of it was
needed to prove the wave's payoff.

Wave 3 planning proposed Wave 4 as its home. **That proposal is withdrawn** — Wave 4 is
dataset-generator only. Video is now unassigned and lives here until a wave claims it.

The groundwork is already done and does not need revisiting: doc 17's input contract
returns a single image and a folder as *the same shape*, with items keyed by an opaque
`item_id` rather than a path, precisely so a frame source can satisfy it without the viewer
changing.

---

## Proposed sequencing

Three groups, ordered. The reasoning matters more than the numbering, since the initiative
currently ends at Wave 6 (Packaging, then Website) and inserting these means renumbering —
a decision deliberately left to Jan at planning time.

| Order | Group | Items | Why here |
|---|---|---|---|
| A | Your own models as annotators | #1, #2 | Closes the product loop, and costs little because Waves 2–3 built the parts |
| B | Foundation-model breadth | #6, #7 | Biggest unknowns (licences, sizes, architectures); wants a stable picker to plug into |
| C | Onboarding & input polish | #3, #4, #5 | Cheap, and **must land before packaging** — but written *after* A and B, or it documents an app that no longer exists |

**Why onboarding is last rather than first.** It is the cheapest group and the most
tempting to do early. But an intro tab and prompt guidance describe how the app works, and
groups A and B both change that: A removes the prompt entirely for trained heads, B adds
concept-prompted models with different prompting rules. Writing the explanation first means
writing it twice. It still has to precede packaging, because packaging ships to people who
have never seen the app.

---

## Group A — Your own models as annotators

### #1 Use a trained backbone + head as an annotation model

*"A now well-trained expert can create bounding boxes for their special case, which the
user then refines."*

The flywheel: annotate → train → **annotate faster with what you trained** → train better.
It is the single item here that makes the earlier waves compound.

- **No prompt when a head is chosen.** A trained head runs its task; there is nothing to
  prompt. The Annotation Studio's prompt field belongs to Grounding DINO, not to the tab.
- Proposals arrive as `provenance` values the user downgrades — Wave 1 already established
  that shape, and a head's output should join it rather than invent a second one.
- Everything needed exists: `run_heads` (doc 18), predictions in source coordinates
  (doc 16), and boxes already in the dataset store's xywh convention.
- **Only `boxes`-hint heads can annotate today.** A segmentation head has no mask-drawing
  tool in the Studio to refine into — that is the same gap #6 hits, see below.

### #2 Choose the model/head upfront in the Inference Viewer

**Check what is actually missing first.** Wave 3 already ships a head picker
(`HeadRunPanel`) that selects heads *before* running, filters by task, derives the backbone
from the selection, and refuses incompatible combinations. Worth confirming with Jan
whether he means: choosing before an image is loaded, persisting the choice across images,
or something the current panel does not do at all. Scoping this from the description alone
risks rebuilding what exists.

Grouped with #1 because both make the head picker a shared, first-class control across two
tabs, and it should be designed once — doc 12's `summary` contract already says it must
read identically in every tab.

---

## Group B — Foundation-model breadth

Both items add *new kinds of model*. They come after Group A so they plug into a picker
that has already been made shared, and they carry the real unknowns.

### #6 SAM 3 and Depth Anything 3

Confirmed to exist and to have open weights (checked 2026-08-18):

| Model | Repos | Licence |
|---|---|---|
| Depth Anything 3 | `depth-anything/DA3-SMALL`, `DA3-BASE`, `DA3-LARGE` | ⚠️ verify per-variant — the nested giant/large is **CC BY-NC 4.0, non-commercial** |
| SAM 3 | Meta, released 2025-11-19 (SAM 3.1 follows) | ⚠️ custom **SAM License** — permissive, runs locally, but *not* MIT/Apache and carries extra conditions |

**The licences are a Wave-5-Packaging problem, not a detail.** This app is meant to be
"sharable, installable". A CC BY-NC variant cannot ship inside a product that is
distributed commercially, and the SAM License needs reading before it is bundled. Weights
are never bundled in the installer (they download on demand), which softens this — but the
catalogue entry still has to state the licence, and the admin panel should show it.

Scope, per Jan: **Inference Viewer first**, because it needs no new labelling tools. The
Annotation Studio comes later and needs a mask-drawing/refining tool that does not exist —
the same gap #1 hits for segmentation heads. Download options go in the admin panel, small
variants as the default.

Two notes on framing:
- **These are not VLMs.** Depth Anything is a monocular depth estimator; SAM 3 is a
  promptable segmentation model. Grounding DINO is open-vocabulary detection. The
  distinction matters because it decides which registry each one joins.
- **SAM 3 is concept-prompted**, so it is closer to a Grounding DINO *alternative* than its
  predecessors were — it takes a text concept and returns masks and boxes. That makes it
  relevant to #7 as well as #6, and possibly the strongest single addition on this list.

### #7 SigLIP 2, and the Gemini question

**SigLIP 2 is not a drop-in Grounding DINO replacement.** It is an image–text embedding
model — it scores how well an image matches text. It does not localise, so it produces no
boxes. Realistic roles, all worth having but none of them "swap out the detector":
- an alternative **backbone** for the head trainer, beside DINOv2/v3;
- **zero-shot classification** labels;
- a **verifier** that re-ranks or filters another detector's proposals.

Pick the role before planning the feature. *(Architecture stated from prior knowledge —
confirm the current repo ids and licence at planning time.)*

**Gemini Flash Vision — my answer: not as a peer of Grounding DINO, and not yet.**

- **There is no local version.** Gemini is API-only; there are no downloadable weights. So
  this is not "another model in the catalogue", it is a different category of thing.
- **It would send the user's images off their machine.** That contradicts the premise the
  whole app is built on — a desktop tool where the model runs locally and the data never
  leaves. Wave 1's threat model says confinement is not the control *because the user picks
  their own folders*; those same folders would now be uploaded.
- **It brings key handling**, per-image cost, rate limits, offline failure and a second
  error taxonomy. `HF_TOKEN` already lives in `.env` and is never committed, so the
  mechanism exists — but a token that gates a download is not the same as a key that is
  charged per call.
- **Where it does fit:** Wave 6 already puts the app on a website with hyperscaler compute,
  where data leaving the machine is the deal the user has already accepted. A cloud VLM
  belongs in that conversation, clearly labelled, never a default, and never silently.

If the goal is "better semantics than Grounding DINO while staying local", **SAM 3 is the
stronger bet** and is already on this list.

---

## Group C — Onboarding & input polish

Cheap, independent of each other, and the last thing before packaging.

### #5 An intro tab explaining the stages

"In detail, for dummies." The app has five tabs and a non-obvious pipeline — annotate →
train a head on a frozen backbone → infer → generate data. Nothing currently explains why
a backbone is frozen, what a head *is*, or why there is no prompt for a trained head.

Write it after A and B, or it describes an app that no longer exists.

### #4 Prompt guidance in the Annotation Studio

Specifically: how to ask for **one** label type versus **several**. Grounding DINO's `a
cat. a dog.` syntax is not guessable, and the current placeholder is the only hint.

Interacts with #1 (trained heads have no prompt at all) and #6 (SAM 3 concept prompts are
different again), so the guidance has to cover which mode the user is in — another reason
it lands after them.

### #3 Drag-and-drop images

Currently a typed path plus a native picker. Under Tauri a file drop yields real paths, so
it feeds doc 17's existing input contract directly and does not need a second one. In a
plain browser it yields `File` objects with no path, which the path-based API cannot
accept — so the browser case either needs an upload endpoint or has to stay picker-only.
Decide that before building.

---

## To verify at planning time

- Per-variant licences for Depth Anything 3, and the full SAM License text.
- Whether SAM 3.1 supersedes SAM 3 for this use.
- SigLIP 2 repo ids, licence, and which of the three roles above is wanted.
- Exact sizes, so the admin panel's disk warnings stay honest (~14 GB free on this machine).
- Whether #2 is asking for anything `HeadRunPanel` does not already do.

---
id: dinotraining-wave-5
title: "Wave 5: Annotate With Your Own Models"
initiative: dinotraining
initiative_version: 7
status: in_progress
depends_on: dinotraining-wave-4
demo_state: "In the Annotation Studio the user picks a trained backbone + head instead of writing a Grounding DINO prompt, and the expert model proposes boxes they refine by hand — the same head picker, reading identically, in both the Studio and the Inference Viewer."
created: 2026-08-19
hash: d351fd66
---

# Wave 5: Annotate With Your Own Models

## Demo-State

In the **Annotation Studio** the user chooses a **trained backbone + head instance**
instead of typing a prompt. There is no prompt field in that mode — a trained head runs
its task; there is nothing to prompt it with. The head's predictions arrive as proposals
in the existing review UX, which the user accepts, downgrades or corrects by hand, exactly
as they do with Grounding DINO's.

The same head picker — same control, same wording, same provenance — serves both the
Studio and the Inference Viewer.
*(Not complete until this can be manually demonstrated.)*

## Why this wave exists

This is the flywheel. Waves 1–3 built annotate → train → infer as a straight line; this is
the step that bends it into a loop: **annotate → train → annotate faster with what you
trained → train better.** It is the item that makes the earlier waves compound rather than
merely accumulate.

It is also cheap, and that is not a coincidence. Every part already exists:
`run_heads` (doc 18) runs N heads over an image, doc 16 returns predictions in *source*
coordinates, and boxes already use the dataset store's xywh convention — so a prediction
can become an annotation without a second conversion.

## Features (draft — refined in plan-wave)

| # | Feature | Depends on |
|---|---------|------------|
| 1 | shared-head-picker | — |
| 2 | studio-head-annotator | shared-head-picker |
| 3 | inference-picker-upfront | shared-head-picker |

- **shared-head-picker** — one control, used by the Studio and the Inference Viewer. Wave 3
  built `HeadRunPanel`; this promotes it to a shared component rather than copying it.
  Doc 12's contract is the whole point: a head must read **identically** in every tab, from
  `HeadInstance.summary` and never from a filename. This wave makes it the fourth consumer
  of that contract.
- **studio-head-annotator** — the Annotation Studio runs a chosen head instead of a prompt.
  Proposals join the existing `provenance` model rather than inventing a second one; Wave 1
  already established that proposals arrive as something the user downgrades.
- **inference-picker-upfront** — **scope this against what already ships.** Wave 3's panel
  already selects heads before running, filters by task, derives the backbone from the
  selection and disables incompatible heads. Confirm with Jan what is actually missing —
  choosing before an image is loaded? persisting the choice across images? — rather than
  rebuilding a working control from a one-line description.

## Scoping settled 2026-08-20 (before execution)

The draft above was written before Wave 4 shipped. Three corrections, made against what
actually exists rather than against the one-line descriptions:

**1. The shared control is `ExpertHeadPicker`, not `HeadRunPanel`.** The draft says promote
`HeadRunPanel`. Wave 4 already built `components/ExpertHeadPicker.tsx` and its docstring
argues explicitly against exactly that promotion: `HeadRunPanel` is a **multi-select built
for comparison** — several heads, several result panes — and both the Generator and the
Studio want *one* head writing into one dataset. Promoting it would force compare semantics
into two tabs with no use for them. So feature 1 becomes: make `ExpertHeadPicker` the shared
component (Studio + Generator), leaving `HeadRunPanel` as the Inference Viewer's comparison
control. What is shared is what must not drift — `name` + `summary`, never a filename, and
filtering on `render_hint`, never on `task`.

**2. `inference-picker-upfront` is real, and small.** `HeadRunPanel` renders behind
`{current && …}` in `InferenceViewerTab.tsx`, so heads genuinely cannot be chosen until an
image or folder has loaded. The fix is lifting the panel out of that guard and holding the
selection across image changes — not rebuilding a working control.

**3. Feature 2 is the wave.** Everything else is plumbing around it.

### Open questions — answered by Jan, 2026-08-20

- **Only `render_hint === 'boxes'` heads may be picked in the Studio.** A segmentation or
  depth head has no refine tool there to correct into, and the Studio's whole promise is
  hand-refinement; offering a head whose output can only be accepted or rejected would
  quietly break that promise in one mode. Wave 4's verdict-only mask review stays in the
  Dataset Generator, where reviewing *is* the task.
- **Head mode and prompt mode are exclusive.** Choosing a head replaces the prompt field
  rather than joining it: one provenance per proposal, one review pass, and the mode is
  unambiguous on screen. Running both was considered — it would show what your head misses
  against Grounding DINO — and rejected for this wave because it doubles the review load and
  needs a near-duplicate rule between two sources that nothing else needs.

## Open Research

- **Only `boxes`-hint heads can annotate.** A segmentation or depth head has no
  mask-drawing tool in the Studio to refine into. Wave 4 brings SAM 3 and mask review for
  the *Dataset Generator*; whether the Studio reuses that surface or stays box-only is the
  main scoping question here.
- **What replaces the prompt field in head mode.** Hiding it is not enough — the user needs
  to see *which* mode they are in, and the two modes produce differently-shaped proposals.
- **Whether a head and Grounding DINO can run together** on one image, or whether choosing
  a head is exclusive. Running both is plausible and doubles the review load.

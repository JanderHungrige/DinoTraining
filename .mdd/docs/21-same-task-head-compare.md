---
id: 21-same-task-head-compare
title: Same-Task Head Compare — A Filtered List, Not a Mode
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-3
wave_status: complete
depends_on: [18-multi-head-compose, 20-inference-overlay-render]
relates: [12-head-instance-registry, 19-side-by-side-viewer]
source_files:
  - apps/frontend/src/components/SideBySideViewer.tsx
  - apps/frontend/src/components/HeadRunPanel.tsx
  - apps/frontend/src/hooks/useHeadRun.ts
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/HeadRunPanel.test.tsx
  - apps/frontend/src/components/SideBySideViewer.test.tsx
data_flow: greenfield
last_synced: 2026-08-18
status: complete
phase: all
mdd_version: 11
tags: [comparison, head-instances, task-filter, n-up, provenance, viewer]
path: Inference/Compare
integration_contracts: []
satisfies_contracts:
  - from: 12-head-instance-registry
    function: HeadInstance.summary
    when: offering the user a head to run
    status: done
    verified_at: "apps/frontend/src/components/HeadRunPanel.tsx:84"
  - from: 12-head-instance-registry
    function: groupByTask(instances)
    when: narrowing the offered heads to one task
    status: done
    verified_at: "apps/frontend/src/components/HeadRunPanel.tsx:34"
  - from: 18-multi-head-compose
    function: run_heads via POST /api/v1/inference/compose
    when: running several heads over one image
    status: done
    verified_at: "apps/frontend/src/hooks/useHeadRun.ts:104"
security_read_sites: []
known_issues:
  - "Only one head per task ships as a default, so a real same-task comparison needs a trained or imported second head. Verified by registering a scratch segmenter, comparing, and removing it again — the mechanism works, but a fresh install cannot demonstrate it without training something first."
  - "Panes are equal-width columns, so five heads on a laptop screen gives five narrow strips. A wrap or a horizontal scroll is the obvious next step; it was left out rather than guessed at, because the useful number of simultaneous heads is not yet known from real use."
  - "The task filter narrows what is *offered* but deliberately keeps an existing selection, so a filtered view can be running a head it is not currently showing. The compare note names the task, but the panes are the honest signal."
sister_projects: []
---

# 21 — Same-Task Head Compare

## Purpose

Run several heads **on the same task** over one image and see their results next to each
other. This is the payoff of the whole instance model: "is the head I just trained better
than the pretrained default?" is a question the app can now answer by looking.

## It is not a separate mechanism

The wave doc is explicit: comparison "is `list_all(task=…)` filtered, rendered N-up; not a
separate mechanism". This feature holds that line — there is **no compare mode to switch
into**, and nothing anywhere branches on how many heads are selected:

- **Filtering** is a task dropdown over `groupByTask` (doc 12), which offers exactly the
  tasks the installed heads cover, so an empty group cannot be chosen.
- **N-up** is `SideBySideViewer` taking a *list* of result panes instead of one overlay.
  One result is the side-by-side case; three is a comparison; the component does not know
  the difference.

Select three segmenters and you get three result panes. Select a segmenter and a
classifier and you get two — a legitimate thing to ask for, just not a *comparison*.

## What changed in feature 19

`SideBySideViewer` took `renderOverlay` / `resultLabel` / `resultPlaceholder` — one result.
It now takes `results: ResultPane[]`, and the grid's column count comes from the list
length rather than a fixed `1fr 1fr`.

**The single transform is what made this cheap.** Doc 19 chose one transform object
rendered twice over two mirrored states; rendering it N times is the same code. Had the
panes each owned a transform and synchronised by events, going from two to four would have
meant a four-way echo problem. The generalisation cost about ten lines because that
decision was already right.

Panes are keyed by **instance id, not position** — deselecting the first of three heads
must not let React reuse its canvas for the second head's mask, which is how one head's
result ends up under another head's label.

## Business Rules

- **Heads are offered by `summary`** — task, provenance, training data, metrics — and
  panes are titled by `head_name`. Never a filename. This is doc 12's cross-tab contract
  and the third consumer of it; Wave 2 shipped a bug from breaking it once already.
- **The task filter changes what is offered, not what is selected.** Narrowing the list
  after picking a head does not silently drop that head — losing a selection with no way
  to tell it happened is worse than a filtered view that is running something off-list.
- **A comparison is only announced when the selection agrees on a task.** A mixed
  selection is valid and simply is not labelled a comparison.
- **The backbone is still derived from the selection** (doc 20), so heads registered for
  another backbone are disabled with an explanation rather than offered and then refused.
- **The cost is shown.** Two same-task heads share a framing and therefore a backbone
  pass, and the panel says `1 backbone pass` — the saving doc 18 built, made visible at
  exactly the moment it pays off.

## Data Flow

Greenfield. Predictions come from doc 18's compose endpoint, rendering from doc 20's
registry, geometry from doc 19.

## Dependencies

`18-multi-head-compose` for the shared pass, `20-inference-overlay-render` for the
overlays, `12-head-instance-registry` for `summary` and `groupByTask`.

## Security

None. No new input, no path, no storage.

## Verified

In the running app. A real same-task comparison needs two heads on one task, and only one
per task ships as a default — so a scratch segmenter was registered directly in the store,
compared, and **removed again** (the head registry is back to its original three).

```
task filter → segmentation      offers 2 heads, hides the classifier and depth head
selection   → both              "Comparing 2 heads on segmentation"
run                             1 backbone pass · 169 ms      ← two heads, one pass
panes                           Original | Scratch segmenter | DINOv2 segmenter (ADE20k)
transforms                      1 distinct across all 3 stages
```

With all three defaults selected (three different tasks): 4 panes, `--viewer-columns: 4`,
2 backbone passes, one transform, and pane titles carrying provenance rather than filenames.

**A false alarm worth recording.** The ADE20k pane appears to pick out the object the
segmenter supposedly misses (doc 20). Sampling the canvas showed it holds exactly two class
colours and the object region is not one of them — what looks like a distinct patch is the
yellow object showing *through* the 55%-opacity mask. Doc 20's claim stands. Reading a
screenshot as evidence would have produced a wrong "correction" to a correct document.

## Known Issues

- **A fresh install cannot demonstrate comparison.** Only one head per task ships as a
  default, so the user must train or import a second one first. The mechanism is verified;
  the out-of-the-box experience of it is not.
- **Panes are equal-width columns**, so five heads gives five narrow strips on a laptop. A
  wrap or horizontal scroll is the obvious next step, left out rather than guessed at until
  real use shows how many simultaneous heads are useful.
- **The filter keeps an off-list selection**, so a filtered view can be running a head it
  is not showing in the list. Deliberate — see Business Rules — but the panes, not the
  list, are the honest signal.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

---
id: 26-generator-review-ui
title: Generator Review UI — Pick a Trained Head, Review What It Proposes
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-4
wave_status: complete
depends_on: [25-expert-annotator, 05-annotation-canvas, 12-head-instance-registry]
relates: [06-annotation-workflow, 21-same-task-head-compare]
source_files:
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/components/ExpertHeadPicker.tsx
  - apps/frontend/src/hooks/useGeneratorSession.ts
  - apps/frontend/src/api/generate.ts
  - apps/frontend/src/api/headInstances.ts
  - apps/frontend/src/types/annotation.ts
  - apps/frontend/src/styles.css
  - backend/app/api/v1/heads.py
routes:
  - GET /api/v1/heads
models: []
test_files:
  - apps/frontend/src/components/ExpertHeadPicker.test.tsx
  - apps/frontend/src/components/GeneratorSetup.test.tsx
  - apps/frontend/src/hooks/useGeneratorSession.test.ts
data_flow: reads-existing
last_synced: 2026-08-19
status: complete
phase: all
mdd_version: 11
tags: [dataset-generator, head-picker, review, render-hint, react, annotation-canvas]
path: Dataset Generator/Review
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The review path is verified by unit tests and by the backend endpoint, not in the browser end to end: no pretrained detection head exists to install, so the tab correctly shows its 'nothing can annotate' empty state on this machine. Same gap as 25-expert-annotator. Drive the full loop once a detector has been trained through Wave 2."
  - "Reviewed boxes cannot be saved yet — that is 27-generated-dataset-writer. The tab says so in place of a disabled Save button, which would read as broken rather than absent."
security_read_sites: []
---

# 26 — Generator Review UI

## Purpose

The Dataset Generator tab, previously an eight-line stub. Point a head you have already
trained at a folder of new images, review what it proposes on the same canvas the
Annotation Studio uses, and — from the next feature — save the result as the dataset for
the next head.

## Why not reuse `HeadRunPanel`

The wave doc said to promote Wave 3's `HeadRunPanel` rather than copy it, on the rule that
a third consumer is the trigger for promotion. Reading it closely, **neither** was right.

`HeadRunPanel` is a *multi-select comparison* panel: several heads over one image, several
result panes, a task filter, a "comparing N heads" affordance. That is its whole reason to
exist, and it is bound to `HeadRunState`. The generator wants exactly **one** head writing
into **one** dataset. Promoting it would have pushed compare semantics into a tab with no
use for them; copying it would have duplicated a picker.

What actually needed sharing is narrower and is now explicit: **heads are presented by
`name` + `KIND_LABELS[kind] · summary`, rendered as the backend composed them, never by a
filename.** That is doc 12's cross-tab contract, and both pickers honour it. `ExpertHeadPicker`
is a small, single-select component that shares the contract without inheriting the
semantics.

## `render_hint` is now on the head instance

The picker must answer "can this head annotate boxes?". The only honest source is the head
type's **`render_hint`**, so `GET /api/v1/heads` now returns it, taken from the registry.

Filtering on `task === 'detection'` instead would have been the same defect a `task ===`
comparison is in `components/overlays/`: capability inferred from a label rather than read
from the contract. A test asserts a head whose task says `detection` but whose hint is
`masks` is **not** offered — because the annotator would refuse it at run time, and the
picker should never have shown it.

An instance whose head type is no longer in the registry — a community import can outlive a
type — reports `labels`, the hint nothing dispatches on, so it cannot end up in an annotator
picker that then fails.

## Three empty states, not one

The fix differs for each, and a single "no heads available" sends the user to the wrong
place:

| Situation | What it says |
|---|---|
| No head produces boxes | Classification/segmentation/depth run in the Inference Viewer; train a detector |
| Detectors exist, none on this backbone | Names the backbone; switch it or train against it |
| Still loading | "Loading heads…", never an empty state |

This is the state the app is genuinely in today — DINOv2 publishes no detection head — so it
is the first thing a user meets, and it had to be worth reading.

## Selection follows the CLAUDE.md rule

Backbones and heads arrive asynchronously. `useState(list[0]?.id ?? '')` would run once,
before the fetch resolves, leaving state at `''` while the `<select>` renders its first
option anyway — the form looks filled in and Start is disabled forever. Only the user's
**override** is stored; the effective value is derived:

```ts
const backboneId = backboneOverride || installed[0]?.id || '';
```

Changing the backbone clears the head override, because the head list is filtered by
backbone and a stale override would keep a head selected that the new backbone cannot run.

Tested by rendering with nothing and letting the data land — the sequence a real load
produces, and the only one that reproduces the bug.

## The stale-proposal guard

A proposal is asynchronous and the user can navigate while it is in flight. Without a guard,
boxes computed for image A land on image B, **in B's coordinate space, looking entirely
plausible** — a silent mislabel rather than a visible error.

`useGeneratorSession` holds a monotonic ticket; navigating increments it and a response
whose ticket is stale is dropped. The test for this was confirmed to fail with the guard
disabled before being trusted.

## `Provenance` had drifted

The frontend's `Provenance` union was still `'grounding-dino' | 'hand-drawn'` — it never
mirrored the backend widening in `22-mask-dataset-store` and `23-mask-annotator-registry`.
Because it is a hand-maintained literal union, nothing failed until something assigned
`expert-head` to it. Now widened, with a comment pointing at the backend constant *and* at
the fact that adding a value there needs a migration.

## Dependencies

- `25-expert-annotator` — the `POST /generate/expert` endpoint this drives.
- `05-annotation-canvas` — the review surface, reused unchanged.
- `12-head-instance-registry` — `summary`, `KIND_LABELS`, and now `render_hint`.

## Known Issues

See frontmatter: the review loop is not browser-verified end to end (no detection head
exists to install), and saving arrives with the next feature.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

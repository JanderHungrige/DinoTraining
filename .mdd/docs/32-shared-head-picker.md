---
id: 32-shared-head-picker
title: Shared Head Picker — One Control, Two Tabs, One Reading
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-5
wave_status: in_progress
depends_on: [12-head-instance-registry, 26-generator-review-ui]
relates: [19-side-by-side-viewer, 33-studio-head-annotator]
source_files:
  - apps/frontend/src/components/ExpertHeadPicker.tsx
  - apps/frontend/src/components/HeadRunPanel.tsx
  - apps/frontend/src/api/headInstances.ts
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/ExpertHeadPicker.test.tsx
  - apps/frontend/src/components/headReading.test.tsx
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [head-picker, shared-component, render-hint, provenance, annotation-studio, dataset-generator]
path: Annotation Studio/Head Mode
integration_contracts:
  - consumer: 33-studio-head-annotator
    function: "ExpertHeadPicker({ legend, groupName })"
    when: "the Studio renders its head-mode picker"
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "`backboneId` is still a required prop rather than being derived from the selected head. Both consumers happen to choose the backbone first, so nothing is wrong today, but a third consumer that wants \"pick a head, infer its backbone\" would have to invert the flow."
sister_projects: []
---

# 32 — Shared Head Picker

## Purpose

Make the control that chooses one trained head serve the **Annotation Studio** as well as
the **Dataset Generator**, so a head reads identically in every tab that offers it.

## Architecture

Wave 5's plan said to promote `HeadRunPanel`. **That was written before Wave 4 shipped and
is the wrong component.** `HeadRunPanel` is a *multi-select built for comparison* — several
heads over one image, several result panes — while both tabs here want exactly one head
writing into one dataset. Promoting it would force compare semantics into two tabs with no
use for them; Wave 4 recorded that reasoning in `ExpertHeadPicker`'s own docstring when it
declined the same promotion.

So the promotion runs the other way: `ExpertHeadPicker` becomes the shared picker,
`HeadRunPanel` stays the Inference Viewer's comparison control, and nothing is copied.

```
ExpertHeadPicker  ──┬──▶  Dataset Generator   legend "Expert head"
                    └──▶  Annotation Studio   legend "Annotate with"   (doc 33)

HeadRunPanel      ─────▶  Inference Viewer    multi-select, comparison (unchanged)
```

## Business Rules

1. **Heads are filtered on `render_hint === 'boxes'`, never on `task`.** The authoritative
   field, and the same defect a `task ===` comparison is in `components/overlays/`. It is
   also what confines the Studio to box heads: a segmentation or depth head has no refine
   tool there to correct into, and the Studio's promise is hand-refinement.
2. **A head is presented as `name` + `summary`, never a filename** — doc 12's contract, of
   which this is now the fourth consumer. The one-line description lives in **one function**,
   `describeHead` in `api/headInstances.ts`. Keeping two *controls* is deliberate;
   keeping two *descriptions* was not — the same template was written out byte for byte in
   both components, so a single edit would have made the Inference Viewer and the Studio
   disagree about the same head with nothing failing. `headReading.test.tsx` renders both
   over one head and asserts they agree, rather than checking each against a literal, which
   would stay green if both drifted together.
3. **`legend` is a prop.** The Generator picks *what proposes*; the Studio picks *what
   annotates*. Same control, different sentence.
4. **`groupName` is a prop.** Radios sharing a `name` form one group, so two pickers on one
   page would silently deselect each other. Nothing renders two today; this is what makes it
   safe when something does.
5. **Three distinct empty states are kept** — nothing installed can propose boxes / none
   matches this backbone / still loading. A single "no heads available" would send the user
   looking in the wrong place.

## Data Flow

Reads `HeadInstanceInfo[]` as the caller already fetched it (`GET /api/v1/heads`). Holds no
state and performs no I/O: the selected id is the caller's, which is what lets the Studio
keep its selection in the same session hook that owns its boxes.

## Dependencies

- **12-head-instance-registry** — `name`/`summary`/`render_hint`, the fields it renders.
- **26-generator-review-ui** — the existing consumer, whose behaviour must not change.

## Security

None. Renders data already fetched; no input, no I/O, no user-supplied paths.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

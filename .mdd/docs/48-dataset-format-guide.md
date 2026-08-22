---
id: 48-dataset-format-guide
title: Dataset Format Guide — What a Training Set Must Look Like
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: complete
depends_on: [31-external-dataset-import]
relates: [38-intro-tab, 39-prompt-guidance, 08-head-trainer-panel]
source_files:
  - apps/frontend/src/tabs/datasetFormat.ts
  - apps/frontend/src/components/DatasetFormatPanel.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/DatasetFormatPanel.test.tsx
  - backend/tests/test_dataset_format_guide.py
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [documentation, onboarding, head-trainer, coco, dataset-import, accessibility]
path: Head Trainer/Help
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**The guide is prose, and prose drifts.** Five backend tests read `datasetFormat.ts` and assert the two claims that are machine-checkable — the annotation filename and the one-level search — but the rest (the `bbox` convention, the positive-only rule, the ignored fields) are asserted only as *present*, not as *correct*. A future change to `coco_import.py` could still make a paragraph wrong."
  - "It documents the **COCO** importer only. YOLO, Pascal VOC and OpenLABEL are named as things to convert *from*, with no converter offered here."
  - "Lives in the Head Trainer, which is where the question is asked, but the import itself is in Datasets. The panel says so; it does not link there."
sister_projects: []
---

# 48 — Dataset Format Guide

## Purpose

> "Add an info button to the training head tab, that explains exactly how a training
> dataset must look like (structure, labels, …) to be usable in this application. This
> allows the user to download random sets and save them correctly."

## Why in the Head Trainer

The question is asked *while* filling in the trainer form, by someone who has just
downloaded a dataset from somewhere and wants to know whether it will load. Not in the
intro tab, which is read once before any of this makes sense, and not in a wiki.

A disclosure button rather than a modal, for the same reason: the answer has to be readable
**next to** the form rather than instead of it.

## What it says

Six sections, and each exists because it is a way people actually get this wrong:

| section | the mistake it prevents |
|---|---|
| The shape on disk | nesting splits two folders deep, where `find_coco_files` will not look |
| The annotation file | absolute `file_name` paths from whoever exported it |
| Boxes | `[x1,y1,x2,y2]`, or a YOLO export's normalised centre coordinates |
| Classes | "category 0 is a placeholder, delete it" — which destroys `blood` |
| What it does not carry | expecting masks or negative verdicts to survive |
| If it will not import | reading the skip counters instead of assuming success |

The **category-0 warning** is there because doc 31 hit it: of the three reference datasets,
`thermal` and `chess` have an unreferenced placeholder at id 0 while `blood`'s id 0 is the
real class `platelets`. Filtering by id would silently delete every platelet annotation and
still report a successful import.

## The drift problem, and what is done about it

This panel makes claims about `coco_import.py`, and **nothing in the frontend can tell
whether they are still true** — the component renders whatever string it holds.

So the *backend* tests read `datasetFormat.ts`. Renaming `COCO_FILENAME` or making the
search recursive now fails a Python test, which is the only place that can notice. One test
goes further and pins the one-level claim against `find_coco_files` itself rather than
against its comment.

That covers the two machine-checkable claims. The rest are asserted only as present, which
is stated plainly in the frontmatter rather than left to be discovered.

## Business Rules

1. **The content is a data module, not JSX.** Prose gets corrected far more often than the
   markup around it, and a diff touching only `datasetFormat.ts` is one a non-React reader
   can check — the same rule `introContent.ts` set.
2. **`aria-expanded` *and* `aria-controls`.** The first tells a screen reader that something
   opened; without the second it does not say what.
3. **The tree scrolls inside itself.** A monospace block must never make the page scroll
   sideways.
4. **The panel is capped at 74ch.** Prose beside a form is measured in characters; a line
   the width of the trainer panel is unreadable however wide the window is.

## Verified

11 frontend tests and 5 backend ones. **Verified in the running app on 2026-08-21**: the
button opens the panel, all six headings render, the directory tree shows with
`overflow-x: auto`, the panel measures 699 px against its 74ch cap, and the page does not
scroll sideways.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

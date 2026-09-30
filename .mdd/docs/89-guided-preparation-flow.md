---
id: 89-guided-preparation-flow
title: Guided Preparation Flow — The "Prepare data" Tab
edition: DinoTraining
depends_on: [81-dataset-audit, 83-safe-fixes, 84-leakage-safe-split, 85-model-input-planning, 86-imbalance-strategy, 87-augmentation-presets, 88-preparation-recipe]
relates: [38-intro-tab, 74-inspect-datasets, 90-training-consumes-recipe, 03-dataset-store]
source_files:
  - apps/frontend/src/tabs/PrepareTab.tsx
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/tabs/introContent.ts
  - apps/frontend/src/App.tsx
  - apps/frontend/src/components/prepare/PrepareSteps.tsx
  - apps/frontend/src/components/prepare/StepNav.tsx
  - apps/frontend/src/components/prepare/AuditStep.tsx
  - apps/frontend/src/components/prepare/FindingCard.tsx
  - apps/frontend/src/components/prepare/FixStep.tsx
  - apps/frontend/src/components/prepare/SplitStep.tsx
  - apps/frontend/src/components/prepare/InputStep.tsx
  - apps/frontend/src/components/prepare/BalanceStep.tsx
  - apps/frontend/src/components/prepare/AugmentStep.tsx
  - apps/frontend/src/components/prepare/OptionList.tsx
  - apps/frontend/src/components/prepare/SaveStep.tsx
  - apps/frontend/src/hooks/usePrepareData.ts
  - apps/frontend/src/hooks/usePreparePlans.ts
  - apps/frontend/src/api/prep.ts
  - apps/frontend/src/api/prepPlan.ts
  - apps/frontend/src/api/prepGuards.ts
  - apps/frontend/src/prepare.css
  - backend/app/datasets/db.py
  - backend/app/prep/balance_plan.py
routes: []
models: []
test_files:
  - apps/frontend/src/tabs/PrepareTab.test.tsx
  - apps/frontend/src/components/prepare/PrepareSteps.test.tsx
  - apps/frontend/src/components/prepare/FixStep.test.tsx
  - apps/frontend/src/api/prep.test.ts
  - apps/frontend/src/components/TabBar.test.tsx
  - backend/tests/test_db_threads.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [data-preparation, guided-flow, frontend, non-experts, recipe, review-sheet]
path: Prepare Data/Flow
initiative: dinotraining
wave: dinotraining-wave-11
wave_status: complete
integration_contracts:
  - function: "a 'Train with this recipe' action that opens Training with the recipe chosen"
    when: "a recipe is saved and up to date"
    satisfied_by: 90-training-consumes-recipe
satisfies_contracts: []
known_issues:
  - "The flow ends at the saved recipe. Starting training from it is doc 90."
  - "Intake (doc 82) is not in the flow: it happens at import, before a dataset exists. The flow starts from a dataset already in the app."
  - "Wave 11 was branched from dev in parallel with Wave 10, so the tab uses the older colour tokens. Both branches define them, so the tab takes Wave 10's look after merging. Check it once both are in dev."
  - "The pane-width browser check found clicks by element reference landing off-target when the viewport was emulated larger than the pane. That is the test harness, not the app; tabs were driven at the pane's own size."
security_read_sites: []
sister_projects: []
---

# 89 — Guided Preparation Flow

## Purpose

Wave 11's backend (docs 81–88) knows what is wrong with a dataset and how to prepare it.
This tab puts that in front of someone who has never trained a model: one step at a
time, a recommended setting at every step, a paragraph on why, and nothing that needs
the words "stratified" or "letterbox" to be understood.

## Where it lives

A tab, **Prepare data**, between Annotation Studio and Training. That is where the work
happens: label, prepare, train. The Intro tab (doc 38) describes it as a stage, and its
test enforces that every tab is described.

## The flow

The dataset and the model to train are picked at the top; both are remembered. Then the
steps:

| # | Step | Status | Recommended |
|---|---|---|---|
| 1 | Check the data (audit, doc 81) | done when audited *for this model* | run it |
| 2 | Fix what is safe (doc 83) | done when there are no copies or unreadable files | keep one copy, drop unreadable |
| 3 | Split (doc 84) | done when split | automatic |
| 4 | What the model sees (doc 85) | choice | the plan's tiling |
| 5 | Unequal classes (doc 86) | choice | the plan's strategy |
| 6 | Changed copies (doc 87) | choice | the domain guess |
| 7 | Save the recipe (doc 88) | done when an up-to-date recipe exists for this model | — |

- The open step is the user's pick, or else the first step not done. Every step is
  clickable, so experts skip ahead.
- **Manual checks are part of the flow.** Each finding shows its example pictures as
  thumbnails ("look at these"): blur, lighting and wrong labels are judged by a person.
- **The class editor** merges, renames or leaves out classes. It shows the saved map, and
  what is edited is only the rows the user changed.
- **"What the model sees"** shows the pictures at the model's own resolution, enlarged
  without smoothing (`image-rendering: pixelated`), with too-small objects in red.
- **Save** shows the choices and the existing recipes, with the reasons any are out of
  date. The server's refusal reason ("Run the Split step first") is shown as it is.

## React rules applied

- **Choices are overrides.** Tiles, strategy and preset are stored as the user's
  override, keyed by dataset and model. The effective value is the override or the
  loaded recommendation. One test renders with no plans and then with plans, which is
  the sequence a real load produces, and asserts the recommendation is selected *and*
  saved.
- **The recipe name** is an override of `"<dataset> for <model>"`.
- **Loads that the user has moved past** (another dataset picked) are dropped, not
  applied.

## Verified live (2026-09-30, Blood cells)

In the running app:
- steps 1–3 and 7 showed as done;
- the saved recipe "blood v1" was listed;
- step 4 showed the plan (448 px letterbox, typical object 82.5 px, 2 % below 28 px, no
  tiles needed) and six pictures at 448 px, the small platelets in red;
- step 5 had "Make rare classes count more" pre-selected, with the weights 1.32 / 0.39 /
  1.3;
- step 6 showed the microscopy guess and the original with three changed versions.

**Found live, and fixed:**
1. **"Cannot reach the backend" on every load**, although every call succeeded. React
   StrictMode cleans an effect up once on mount, and the aborted request reports itself
   as unreachable. It is now ignored when the request was aborted. The test renders in
   StrictMode, and it failed before the fix.
2. **The recipe list failed intermittently** with a 500, seen by the browser as
   `ERR_FAILED`, and once with a false "Dataset not found". This was a concurrency bug
   in the shared SQLite connection, present since doc 03 and made likely by this tab's
   parallel requests. It is fixed in `transaction()` (doc 03, Bugs), with two
   reproducing tests.
3. **The balance options contradicted the recommendation.** The option texts claimed
   "best for boxes" for sampling while weighting was recommended for these boxes. The
   texts now state the rule.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

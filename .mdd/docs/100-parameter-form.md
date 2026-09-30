---
id: 100-parameter-form
title: Parameter Form — "Plain name (technical term)", a ? with Explanation and Default, Basic/Advanced
edition: DinoTraining
depends_on: [99-parameter-catalogue, 69-remembered-entries, 97-finetune-ui]
relates: [99-parameter-catalogue, 101-default-recipes]
source_files:
  - apps/frontend/src/api/parameters.ts
  - apps/frontend/src/hooks/useParameters.ts
  - apps/frontend/src/components/params/ParameterForm.tsx
  - apps/frontend/src/components/params/ParameterField.tsx
  - apps/frontend/src/components/params/HelpPopover.tsx
  - apps/frontend/src/params.css
  - apps/frontend/src/components/TrainerForm.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/components/finetune/FoundationFinetunePanel.tsx
  - apps/frontend/src/api/training.ts
  - apps/frontend/src/api/finetune.ts
routes:
  - GET /api/v1/training/parameters/{model_id}
models: []
test_files:
  - apps/frontend/src/components/params/ParameterForm.test.tsx
  - apps/frontend/src/hooks/useParameters.test.tsx
  - apps/frontend/src/components/finetune/FoundationFinetunePanel.test.tsx
  - apps/frontend/src/components/TrainerForm.test.tsx
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [training, fine-tuning, parameters, help, accessibility, non-experts, frontend]
path: Training/Parameters/Form
initiative: dinotraining
wave: dinotraining-wave-13
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 100 — Parameter Form

## Purpose

Jan's request, the visible half: every parameter is labelled like "Rounds (epochs)" and
followed by a **?** that gives a short explanation and a good default.

One component renders doc 99's catalogue for any model. That replaces:
- the head form's three hand-written fields (epochs, learning rate, patience);
- the fine-tune panel's rounds and blocks.

## Architecture

- **`api/parameters.ts`:** `getParameters(modelId)` returns the family (doc 99's
  `ParameterSetInfo`), guarded like every other API module.
- **`useParameters(modelId)`:**
  - loads the family for the chosen model;
  - keeps **only the user's overrides**, remembered per family (doc 69,
    `params.<family>`), and derives the effective values as defaults ⊕ overrides.

  This is CLAUDE.md's rule: nothing is seeded from the asynchronously loaded catalogue.
  Before the catalogue arrives, `values` is empty and the form shows "Loading settings…".
  It returns `set`, `values`, `overrides`, `change(key, value)`, `reset(key)`,
  `resetAll()` and `invalid` (the keys whose override is out of range).
- **`ParameterForm`:**
  - *Basic* fields first;
  - then a collapsed `<details>` titled **Advanced settings (N changed)**;
  - a **Reset all to defaults** button, shown only when something changed.
- **`ParameterField`:** one row.
  - **Label:** "Plain name (technical term)".
  - **A ? button** (`HelpPopover`).
  - **The input:** number, checkbox or select, by kind.
  - **When changed:** a "changed" mark and a ↺ reset for that field.
  - **When out of range:** a message at the field ("Between 1 and 200").
  - **With a recipe chosen:** a field the recipe overrides is disabled, with "Set by the
    recipe".
- **`HelpPopover`:**
  - The **?** is a real `<button>` with `aria-expanded`, `aria-controls` and the name "About
    <label>".
  - The popover shows the explanation, **"Default: <value>"** and why.
  - Esc and a click outside close it. Esc returns focus to the button.
  - The input's `aria-describedby` points at a visually hidden copy of the explanation, so
    a screen reader hears it without opening anything.

## Wiring

- **Head form:**
  - `TrainerSelection` loses `epochs`, `learningRate` and `earlyStoppingPatience`.
    Remembered selections that still carry them keep loading (`isShapeOf` ignores extra
    keys).
  - The run sends every catalogue value; the backend's `TrainingRequest` has a field for
    each.
- **Fine-tune panel:**
  - `epochs`, `learning_rate` and `seed` go as fields; every other value goes in `options`.
  - The hardcoded `learning_rate: backbone ? 1e-3 : 1e-4` is gone, because the catalogue
    has it per model.
- **Start is disabled** while any value is out of range, with the field named beside the
  button.

## Business Rules

1. **The form shows only what the catalogue lists.** No field is hand-written in a
   component.
2. **Overrides are per family:** SAM 2's box jitter does not leak into SAM 3.
3. **Out-of-range input is never sent.** The backend would refuse it (422), but the field
   says so first.
4. **Numbers keep their precision:** a learning rate of 0.0001 is not rounded away by the
   input's `step`.

## Found while building

- **Clearing a number field wrote "NaN" into it.** The draft is re-synced from the value,
  and NaN never equals NaN.
  - **Fix:** a cleared or half-typed number ("1e-") counts as the same "not a number yet"
    and is left alone.
  - **Persistence:** such a value is stored as JSON `null`. Reading back now drops that one
    entry instead of rejecting the whole record, which would forget every change.

## Verified (2026-09-30)

- **Tests:** frontend 989 green, typecheck clean.
- **Running app, Training → Fine-tune a model (RF-DETR):**
  - The ? on Rounds opens the explanation with "Default: 10 — Detectors keep improving…",
    and Esc closes it.
  - *Advanced settings* opens weight shrinkage, gradient limit, backbone blocks and seed.
- **Running app, Training → DINO head:** Rounds 20, Learning speed 0.001, Pictures per step
  1, Patience 5, with Advanced folded.

## Bugs

(none yet)

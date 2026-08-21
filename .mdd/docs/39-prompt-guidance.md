---
id: 39-prompt-guidance
title: Prompt Guidance — Which Prompt Is This, and How Do I Write It
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7
wave_status: in_progress
depends_on: [06-annotation-workflow, 33-studio-head-annotator]
relates: [04-grounding-dino-annotator, 26-generator-review-ui, 38-intro-tab]
source_files:
  - apps/frontend/src/components/FieldHint.tsx
  - apps/frontend/src/components/promptGuidance.ts
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/promptGuidance.test.ts
  - apps/frontend/src/components/SessionSetup.test.tsx
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [onboarding, prompting, grounding-dino, accessibility, annotation-studio, dataset-generator]
path: Annotation Studio/Prompting
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "The guidance is static prose, not validated against what the user typed. A prompt with no full stop between two phrases reads as one long phrase to Grounding DINO and gets poor matches; nothing warns. Checking the *shape* of a prompt is a real feature and a bigger one than this."
  - "The Generator's two concept hints still live inline in `GeneratorSetup` rather than in `promptGuidance.ts`. Moving them is safe but touches a Wave 4 file for no behaviour change, so it was left; the shared home exists for whoever adds a fourth mode."
sister_projects: []
---

# 39 — Prompt Guidance

## Purpose

Explain how to ask for **one** label type versus **several** in Grounding DINO's actual
syntax — and, since by this wave "the prompt" is three different things, make it clear which
one you are looking at.

## Architecture

By Wave 7 a prompt is one of three, and the field itself does not say which:

| Mode | Where | What to say |
|---|---|---|
| Grounding DINO text | Annotation Studio, prompt mode | full-stop separated phrases |
| A trained head | Annotation Studio, head mode | **no prompt** — and what it looks for instead |
| A concept | Dataset Generator | one phrase for SAM 3, several for Grounded SAM |

The wording lives in `promptGuidance.ts`; the rendering in `FieldHint`.

**`FieldHint` exists for one rule.** The hint renders *outside* the `<label>` and is
associated by `aria-describedby`. Text inside a label joins the field's accessible name, so
a paragraph there is read out in full on every focus — a sentence that helps once becomes
something a screen-reader user hears every visit. Wave 4 got this right inline in
`GeneratorSetup` and wrote the reason in a comment; this promotes the comment to a component
so the next field cannot re-derive it wrong.

## Business Rules

1. **The several-labels form is shown literally.** `a bolt. a nut. a washer.` — the full
   stops are the whole trick, and a placeholder alone does not convey it.
2. **Over-proposal is stated up front.** Open-vocabulary detection finds things you did not
   ask for by design. Someone who is not told reads the extra boxes as a broken app rather
   than as work to reject.
3. **Head mode answers the question the missing field raises.** Not "there is no prompt"
   but "this head was trained to find *dog, person* — it proposes those and nothing else."
   Explaining an absence is worth less than saying what happens instead.
4. **A long class list is summarised.** The chess head has thirteen; printing them all turns
   a hint into a wall. Four, then "and N more".
5. **An empty `class_names` still gets a useful sentence.** Pretrained defaults can arrive
   with none, and "trained to find ." is worse than a general statement.

## Data Flow

`headModeHint` reads `class_names` from the head the user selected — the same
`HeadInstanceInfo` the picker renders, so the hint cannot name a different head from the one
that will run.

## Dependencies

- **33-studio-head-annotator** — the mode switch this describes.
- **06-annotation-workflow** — the Studio's prompt field.

## Security

None.

## Verified

In the running app on 2026-08-20. Prompt mode shows the Grounding DINO syntax and the field
carries `aria-describedby="prompt-hint"`. Switching to head mode removes the prompt field
and the syntax hint together, and shows: *"No prompt here: this head was trained to find
bishop, black-bishop, black-king, black-knight and 9 more…"* — the chess head's real
classes, summarised, read from the instance the picker had selected.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

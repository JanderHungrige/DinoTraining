---
id: 33-studio-head-annotator
title: Studio Head Annotator — Annotate With What You Trained
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-5
wave_status: in_progress
depends_on: [06-annotation-workflow, 25-expert-annotator, 32-shared-head-picker]
relates: [05-annotation-canvas, 29-generated-dataset-writer, 31-external-dataset-import]
source_files:
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
routes: []
models: []
test_files:
  - apps/frontend/src/hooks/useAnnotationSession.head.test.ts
  - apps/frontend/src/components/SessionSetup.test.tsx
  - apps/frontend/src/hooks/session.testkit.ts
data_flow: writes-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, expert-head, flywheel, proposal-source, provenance, react]
path: Annotation Studio/Head Mode
integration_contracts: []
satisfies_contracts:
  - from: 32-shared-head-picker
    function: "ExpertHeadPicker({ legend, groupName })"
    when: "the Studio renders its head-mode picker"
    status: done
    verified_at: "apps/frontend/src/components/SessionSetup.tsx:214"
security_read_sites: []
known_issues:
  - "The backbone is pinned to `dinov2-small` (`BACKBONE_ID`), matching what the Dataset Generator does. Correct while that is the only installed backbone; the moment a second one is installed both tabs need a backbone control, and the constant is the thing to grep for."
  - "Head mode reuses the prompt mode's threshold slider and its 0.30 default, which is tuned for Grounding DINO rather than a trained head. Same finding doc 31 recorded for the Dataset Generator, and it wants the same per-head fix in both places."
  - "Switching mode after starting a session means going back through **Change folder**. The mode lives in the config, so changing it restarts the session — acceptable while a session is one folder, worth revisiting if sessions get longer."
sister_projects: []
---

# 33 — Studio Head Annotator

## Purpose

Let the Annotation Studio propose boxes with **a head you trained** instead of a Grounding
DINO phrase. This is the step that bends annotate → train → infer from a line into a loop:
annotate, train, then annotate faster with what you trained.

## Architecture

The mode is chosen **once**, in `SessionConfig`, and nothing downstream re-decides it. The
same canvas, the same three verdicts, the same save path — only the call that produces the
proposals differs.

```
SessionSetup ──▶ SessionConfig.source
                   ├─ { kind: 'prompt', prompt, boxThreshold, textThreshold }
                   │        └──▶ POST /api/v1/annotate          (doc 04)
                   └─ { kind: 'head', backboneId, instanceId, scoreThreshold }
                            └──▶ POST /api/v1/generate/expert   (doc 25)
                                          │
                        both return boxes in *source* pixels, already carrying
                        their own provenance ──▶ AnnotationCanvas ──▶ save (doc 03)
```

**`ProposalSource` is a discriminated union, not optional fields.** The two modes are
exclusive by decision, and optional fields would make "a prompt *and* a head"
representable — at which point every consumer has to decide what that means, which is how
a rule stops being a rule. The union makes the invalid state unconstructible, and `tsc`
found both call sites the moment it landed.

No backend work. `POST /api/v1/generate/expert` already does exactly this for the Dataset
Generator; this feature is the Studio becoming its second caller.

## Business Rules

1. **Head mode replaces the prompt, it does not join it.** Running both was considered —
   it would show what your head misses against Grounding DINO — and rejected for this wave:
   it doubles the review load and needs a near-duplicate rule between two sources that
   nothing else needs.
2. **The mode is visible, not merely implied.** The setup form uses radios rather than
   hiding a field, and the run button reads **"Run head"** or **"Run prompt"** — by review
   time the radios are behind *Change folder*, so the button is the only thing left on
   screen that knows.
3. **Only `render_hint === 'boxes'` heads are offered** (doc 32's filter). A segmentation
   or depth head has no refine tool in the Studio to correct into, and hand-refinement is
   the Studio's whole promise.
4. **Hand-drawn boxes survive a re-run**, exactly as in prompt mode — they are work the
   model cannot reproduce.
5. **No image-level prompt is sent in head mode.** `replace_image_boxes` falls back to it
   when a box carries none; here every box carries its own class, so the fallback must not
   fire. An invented image-level phrase would overwrite nothing and still be a fiction.
6. **The head selection is derived, never seeded into `useState`.** Only the user's override
   is stored; the effective head falls back to the first compatible one. Seeding from an
   async fetch is this project's most-repeated bug.

## Data Flow

`ExpertProposalResponse.boxes` → `toCanvasBoxes` (generate) → `CanvasBox[]` carrying
`provenance: 'expert-head'`, the class as `text`, the score, and the producer snapshot →
`saveImageBoxes`, which renames `text` to `prompt` (doc 31) → `boxes` rows.

Verified against the real store on 2026-08-20: a thermal frame proposed one box at 0.32,
saved as `expert-head | person | 0.32` with a NULL image-level prompt.

## Dependencies

- **25-expert-annotator** — the endpoint, unchanged.
- **32-shared-head-picker** — the control, with the Studio's own legend and group name.
- **06-annotation-workflow** — the session, canvas and save path this extends.

## Security

None new. No new endpoint, no new user-supplied path: the folder field is doc 17's, already
the Studio's input.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

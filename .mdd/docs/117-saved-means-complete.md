---
id: 117-saved-means-complete
title: Saved Means Complete — a Picture Counts for the Classes That Existed When It Was Saved
edition: DinoTraining
depends_on: [103-phrase-data-model, 108-prompts-and-hard-negatives, 115-umbrella-terms]
relates: [118-new-class-question, 119-add-only-review, 104-annotation-target, 107-task-aware-preparation]
source_files:
  - backend/app/datasets/completeness.py
  - backend/app/datasets/annotation_targets.py
  - backend/app/prep/task_facts.py
  - backend/app/i18n/de_targets.py
  - apps/frontend/src/hooks/usePromptClasses.ts
  - backend/app/finetune/phrase_data.py
  - backend/app/finetune/adapters/sam3_queries.py
  - backend/app/api/v1/dataset_phrases.py
  - backend/app/prep/findings_task.py
  - backend/app/i18n/de_audit_task.py
  - apps/frontend/src/lib/pictureChecklist.ts
  - apps/frontend/src/components/TargetGuide.tsx
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
routes:
  - GET /api/v1/datasets/{dataset_id}/completeness
models:
  - images
  - dataset_classes
  - image_phrase_status
test_files:
  - backend/tests/test_completeness.py
  - backend/tests/test_sam3_queries.py
  - backend/tests/test_prep_findings_task.py
  - apps/frontend/src/lib/pictureChecklist.test.ts
  - apps/frontend/src/hooks/usePromptClasses.test.ts
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [sam3, completeness, hard-negatives, phrases, annotation-studio]
path: Datasets/Phrases/Completeness
initiative: dinotraining
wave: dinotraining-wave-15-5
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Timestamps have one-second resolution: a class made in the same second a picture is saved counts as existing before it (the picture is known). Harmless in practice."
  - "A recipe's class map (doc 90) renames classes for training; a renamed class has no `since` under its new name and is treated as known everywhere — as before this doc."
  - "Only the Studio stores its prompt's terms as classes. A Generator run's concept terms exist from their first saved appearance, so frames saved before a term was first found are unknown for it (safe, fewer negatives)."
security_read_sites: []
sister_projects: []
---

# 117 — Saved Means Complete

## Purpose

- **Jan's working rule:** "When annotating, all objects are marked. Pictures that are not
  annotated do not enter the dataset."
- **So:** a saved picture is complete for every class that existed when it was saved, and
  no per-picture check is needed.
- **The one real exception:** a class added later. The pictures saved before it were never
  looked at for it, and must not teach "no m10 here".

## The rule

A picture P is **known** for class C when any of these holds:
1. **An explicit check** for C on P exists (`image_phrase_status`, doc 103). Explicit
   always wins: `complete` or `absent`.
2. **P was saved after C existed:** `P.annotated_at >= since(C)`.
3. **C's start is unknown** (no timestamp at all). This keeps datasets without the data
   working as before.

**`since(C)`**, the moment the class came into existence in this dataset, is the earliest
of:
- its `dataset_classes.created_at` (made in the picker, or ensured for a prompt, see below);
- the earliest `annotated_at` of a picture carrying C on a box or mask;
- the dataset's `created_at`, when C is a term of the dataset's own prompt.

**Otherwise P is unknown for C.** Training leaves it out for C: no positive, and no
"none here".

`annotated_at` is refreshed by every save, so opening an old picture and saving it again
with m10 in mind makes it known for m10. That is exactly the add-only review of doc 119.

### Classes the Studio is asked for

- **The problem:** if a prompt asks for "m8, m9, m10" from the first picture and m10 first
  appears on picture 3, the earliest-appearance rule would leave pictures 1–2 unknown for
  m10. That is safe, but it wastes negatives.
- **The fix:** starting a Studio session with a prompt source ensures a stored class for
  each prompt term (`POST /datasets/{id}/classes`, idempotent). The class then exists from
  the session's start.

## Training (`sam3_queries`, replacing doc 108's "checked mode")

Per picture and class or phrase:

| State | Outlines here | Query |
|---|---|---|
| explicit `absent` | — | `absent` negative |
| known | yes | positive (plus its look-alikes) |
| known | none | `cross` negative, for a class that is not unclear here |
| explicit `complete` | none | skipped (a contradiction, as in doc 108) |
| unknown | yes | skipped |
| unknown | none | `rejected` if an outline of it was rejected here, else nothing |

- **Doc 108's per-phrase "checked mode" is gone.** Checking one picture no longer takes the
  automatic negatives away from the unchecked ones; the timestamps decide.
- **Older sub-phrases** (Wave 14) take their class's state. They are never a cross
  negative, as before.
- **Umbrella terms** (doc 115) use the same per-member state.

## API

- `GET /datasets/{id}/completeness` returns, per class, `since` and `unknown` (the number of
  saved, not excluded pictures that are unknown for it).
- It feeds the audit, and the questions of docs 118 and 119.

## Studio and audit

- **The per-picture checklist** (doc 104, layer `picture-status`) no longer counts clicks:
  - "Saved = complete for N classes", or "not saved yet";
  - with an explicit check it says "checked by hand".
- **The audit per task** (doc 107) reports, per class with unknown pictures:
  "N pictures were saved before class X existed". The action points to "Review for X"
  (doc 119).

## Imports

- An import writes every picture at import time, and its categories appear at import time.
  An imported dataset is therefore complete for its categories.
- That is right for most COCO exports. For one that is not, the folded checks (doc 116)
  remain the override.

## Verified (2026-09-30)

- **Tests:**
  - `test_completeness.py` (5, with an injected clock instead of rewritten timestamps):
    - a class made later leaves older pictures unknown;
    - a prompt term exists from the dataset's start;
    - a hand check or a new save makes a picture known;
    - training reads the same rule.
  - `test_sam3_queries.py`: doc 108's checked-mode tests are rewritten.
    - A picture saved before a class existed teaches only via hand checks.
    - A check elsewhere no longer removes negatives.
    - A sub-phrase follows its class.
  - The audit tests: `saved-before-class` replaces `unchecked-pictures` and
    `no-confirmed-negatives`, and the German coverage still fires every rule.
  - Frontend: the checklist line and `usePromptClasses`.
  - Suites: backend 1841 green, frontend 1078 green; ruff, mypy and tsc clean.
- **Live, on "Wave 12 filled-ring convention" (restarted backend):**
  - `/completeness`: blob and ring, 0 unknown.
  - After creating class "star": star, 70 unknown.
  - A SAM 3 audit in German showed "70 von 70 Bildern wurden gespeichert, bevor es die
    Klasse star gab", with what, why and action in German; the old findings are gone.
  - Class star was deleted again, and completeness went back to blob and ring only.
- **Found while building:**
  - A test first aged a picture with SQL, but the dataset row is restored from its
    manifest, so the dataset's own date would not move. The test now injects a clock.
  - `ruff format tests` reformatted about 60 unrelated test files. They were restored;
    format only the files you changed.

## Bugs

(none yet)

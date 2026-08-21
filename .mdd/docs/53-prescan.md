---
id: 53-prescan
title: Prescan — Only Show Me the Images Worth Looking At
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: in_progress
depends_on: [32-studio-session-setup, 42-foundation-boxes-everywhere, 11-training-job-runner]
relates: [47-box-review-list, 49-osdar23-rail, 50-dataset-as-source]
source_files:
  - backend/app/ml/annotators/prescan.py
  - backend/app/ml/annotators/prescan_runner.py
  - backend/app/api/v1/prescan.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/prescan.ts
  - apps/frontend/src/hooks/usePrescan.ts
  - apps/frontend/src/components/PrescanPanel.tsx
  - apps/frontend/src/lib/prescanSource.ts
  - apps/frontend/src/hooks/useAnnotationSession.ts
  - apps/frontend/src/tabs/AnnotationStudioTab.tsx
routes:
  - POST /api/v1/generate/prescan
  - GET /api/v1/generate/prescan/{job_id}
  - POST /api/v1/generate/prescan/{job_id}/cancel
models: []
test_files:
  - backend/tests/test_prescan.py
  - apps/frontend/src/components/PrescanPanel.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [annotation-studio, prescan, filtering, job-runner, object-detection]
path: Annotation Studio/Prescan
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - backend/app/api/v1/prescan.py (image_paths are read directly; capped at MAX_IMAGES)
known_issues:
  - "**One scan at a time, on its own worker.** A second scan queues behind the first. A shared worker with training would be worse — a scan queued behind a six-minute fine-tune looks hung — but two scans still serialise with no indication."
  - "**The Studio only.** The Dataset Generator would benefit at least as much (it processes a whole folder unattended) and does not have it."
  - "The prompt branch hard-codes `grounding-dino-tiny`, because the session does not carry a model id for prompt mode. Correct today; wrong the moment a second grounding model is offered."
  - "Results are held in memory and lost on restart, like every other job runner here. A 400-image scan repeated after a restart is minutes wasted."
  - "**Label matching is substring, both ways.** Forgiving on purpose, but `signal` matches `signal_pole`, so filtering for one class of a multi-class detector can keep more than asked."
  - "The scan runs the model twice over any image the user then annotates — once to decide it is worth showing, once to propose. Caching the proposals would halve that and would mean holding boxes for hundreds of images."
sister_projects: []
---

# 53 — Prescan

## Purpose

> "Let's say we have the large train dataset, now we want to annotate for person. There are
> a lot of images without a person, so that would mean taking a lot of time skipping the
> dataset."

A folder of 400 rail frames has a person in 30 of them. Reviewing it means pressing Next 370
times to confirm nothing is there — the work this app exists to remove, being done by hand.

## The same model, deliberately

Prescan runs **whichever proposer the session is configured with**. Filtering on one model's
opinion and annotating with another's would make every disagreement look like a bug in the
proposer, and there would be no way to tell from the screen which had happened.

`lib/prescanSource.ts` is the single mapping from a `ProposalSource` to a scan request, for
the same reason: a second mapping, even a correct one today, is how the two drift.

## Nothing is written

A miss is **not recorded**. The store never learns that an image was scanned and found
empty.

Jan chose this over recording checked-and-empty, and the reason is that a model's silence is
not an annotation. Writing one would put a judgement in the dataset that nobody made, and
would teach the next training run that those images are background on the authority of a
model that may simply be wrong.

That is also what makes the escape hatch cheap. The filter is a **checkbox**, the full list
stays loaded, and turning it off re-reads nothing — so "actually, let me check every image"
costs one click and undoes nothing. The user asked for that explicitly, and it is the part
the rest of the design is arranged around.

## Business Rules

1. **An empty label box means "anything the model finds".** The right default for a
   single-class head: asking the user to retype the only class it knows is a question with
   one answer.
2. **Label matching is case-insensitive substring, either way.** The class a proposer
   reports is not always the phrase the user typed — Grounding DINO re-segments its prompt
   (`chess piece` comes back as `chess`), and a fine-tuned detector's names come from its
   dataset. Exact matching would return zero hits and read as "the model found nothing".
   Forgiving in the cheaper direction: a false hit is rejected in one click, a false miss
   hides an image the user never learns existed.
3. **A box with no score always counts.** Hand-drawn and imported boxes carry none, and
   treating that as 0 would hide them behind any threshold at all.
4. **An unreadable image is counted and skipped**, never fatal — one truncated PNG in four
   hundred frames must not lose the other 399 — and the count is **reported**, so a scan
   that quietly read almost nothing cannot pass for one that found almost nothing.
5. **A failing model fails the job.** "Nothing found" and "the model never ran" must not
   look the same.
6. **Cancelling keeps the hits.** The user asked it to stop, not to throw away the answer
   it had already reached.
7. **The job's three counters are read together**, through one locked snapshot. Read
   separately they can disagree — 8 scanned with 9 hits — which reads as a counting bug
   rather than as a race.

## Verified

**End to end on real data, 2026-08-21.** The OSDaR23 holdout (80 tiles) scanned with the
fine-tuned rail RF-DETR for `person` at 0.4:

```
complete  80 / 80   hits 20   unreadable 0
  078_…_r2c3.png  boxes 2  best 0.88  ['person']
  079_…_r2c3.png  boxes 2  best 0.88  ['person']
```

**20 of 80** — sixty images the user does not have to page through.

Then through the UI: the panel reported *"20 of 80 images matched"*, ticking *Show only the
20 matches* took the counter from `Image 1 / 20` and landed on `078_…_r2c3.png`, which
opened with the dataset's own eight ground-truth boxes already on the canvas (doc 50) and
listed in the review panel (doc 47) — `signal ×5, signal_pole, person ×2`, all scoreless,
which is correct for imported boxes.

27 backend tests and 16 frontend.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

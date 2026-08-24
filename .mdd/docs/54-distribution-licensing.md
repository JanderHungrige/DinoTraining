---
id: 54-distribution-licensing
title: What You Must Deal With Before Shipping — and Bulk Cleanup
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-8
wave_status: complete
depends_on: [35-model-licence-surfacing, 51-library-tab]
relates: [36-depth-foundation-model, 30-sam3-annotator]
source_files:
  - backend/app/ml/registry.py
  - backend/app/api/v1/models.py
  - apps/frontend/src/components/DistributionNotice.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/api/models.ts
  - apps/frontend/src/hooks/useLibrary.ts
  - apps/frontend/src/tabs/LibraryTab.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/components/DistributionNotice.test.tsx
  - apps/frontend/src/tabs/LibraryTab.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [licensing, packaging, distribution, admin, library, bulk-delete]
path: Admin / Models/Distribution
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**`redistribution` is set by hand per model, and nothing checks it against the licence string.** That is deliberate — doc 35's reasoning for `non_commercial` applies unchanged: substring-matching 'NC' or 'AGPL' works until a licence is worded differently and fails silently in the direction that matters. But it does mean a new catalogue entry defaults to `free` and nobody is told."
  - "**`non_commercial` and `redistribution` can disagree.** Two fields describing overlapping things, kept separate because `non_commercial` is read in several places already. Nothing asserts `non_commercial === (redistribution === 'non-commercial')`."
  - "**Nothing checks the installer.** This is a notice, not a build gate. Wave 8 packaging should refuse to build with a restricted model in the cache, or exclude it — the notice only helps someone who reads it."
  - "SAM 3's Meta licence is marked `restricted` rather than summarised, which is honest but means the app cannot tell the user whether their specific use is allowed. Someone has to read the terms."
  - "The bulk delete is sequential, so eleven items are eleven round trips. Fine at this scale; a store with hundreds would want batching, which the routes do not offer."
sister_projects: []
---

# 54 — Distribution Licensing, and Bulk Cleanup

## Purpose

Tell the user what shipping this app obliges, and make clearing the leftovers one action.

## The premise this corrects

Jan's framing was *"those specific models are not allowed to be commercially distributed…
and they need to be deleted in the Admin tab before being distributed."*

That is right for one of the three cases and **wrong for the most consequential one.**

| licence | what it actually obliges | "delete before shipping"? |
|---|---|---|
| **CC BY-NC 4.0** — Depth Anything V2 base, large | No commercial use or distribution at all | **Yes.** Jan's model fits exactly |
| **AGPL-3.0** — both YOLO routes Wave 7.5 evaluated | **Commercial use is fine.** Distributing obliges releasing *this whole app's source* under AGPL | **No.** It is a decision about the app's own licence, not a file to remove |
| **Meta SAM License** — SAM 3 | Custom terms; not a standard licence and not summarisable | Read them |

Collapsing these into "non-commercial" is how someone concludes a YOLO cannot be sold —
when it can, and the real cost is that the whole app becomes AGPL. That is a much larger
decision than deleting a file, and it is precisely the Wave 8 question already parked in
`HANDOFF.md`. **Nothing AGPL is in the tree**; `copyleft` is defined so that if a YOLO is
ever added, the app says the true thing rather than the convenient one.

## The notice

Lives in **Admin**, because that is where the fix is — the remove button is a few
centimetres below. A notice in the Library would name a problem and point elsewhere.

Three properties worth keeping:

1. **It lists what is *installed*, not what is catalogued.** The constraint is a property of
   what the user downloaded. Currently that is one entry: SAM 3.
2. **It disappears when there is nothing to say.** A standing warning that never changes is
   one the user stops reading.
3. **Three obligations get three sentences**, from `REDISTRIBUTION_NOTES` keyed by the
   value, so the Admin panel and any future installer check cannot describe the same
   licence differently.

## Bulk delete

The Library (doc 51) could delete one thing at a time. Clearing eleven verification
leftovers was eleven confirmations, which is why cleaning up did not happen.

1. **Selection is keyed `kind:id`, never a bare id.** Three stores answer to opaque ids and
   a bare one could name a dataset and a head at once.
2. **Deletes run sequentially, not `Promise.all`.** Deleting a dataset and a head that
   references it simultaneously races the store, and that failure leaves half a thing.
3. **The confirmation names every item.** Eleven checkboxes are easy to mis-tick and this is
   the last chance to see it.
4. **One refresh, after all of them**, and the error is set *after* the refresh — doc 51's
   bug, which would otherwise have been reintroduced verbatim.
5. **The checkbox label carries name *and* detail.** Found by using it: four heads were all
   called `Object detection: dog, person`, differing only in what they trained on and their
   mAP. Four identical labels is a real ambiguity for anyone not reading the row visually.

## The thermal cleanup, as it happened

Jan asked for every head and dataset related to thermal. **Eleven items**, and the
interesting part is that a name-based sweep would have found seven:

```
datasets   Thermal flywheel check · Thermal from expert head ×2 · Thermal, auto-proposed
           Thermal dogs and people (203 images, the HuggingFace import)
heads      Object detection: dog, person  ×4      <- no "thermal" in the name
fine-tunes Studio thermal detector · Thermal RF-DETR
```

The four heads were caught by the row's **`from Thermal dogs and people`** metadata — doc
51's decision to resolve `dataset_ids` to names rather than show ids, doing work it was not
designed for.

Jan chose to include the 203-image import, so **doc 43's and doc 44's thermal numbers are
now unreproducible without re-importing from HuggingFace.** They stand in those docs as a
record. Verified after: 0 thermal datasets, 0 dog+person heads, 0 thermal fine-tunes.

## Verified

**In the running app on 2026-08-21.** The notice shows one entry — `facebook/sam3`, badged
*SAM License (Meta, custom)*, with the vendor-terms sentence — and nothing else, because
the two CC BY-NC depth models are not installed. The bulk bar selected 11, listed all 11 by
name in the confirmation, and the store afterwards held 16 datasets, 14 heads and 2
fine-tunes with nothing thermal in any of them.

11 tests on the notice, 12 on bulk delete.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

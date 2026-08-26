---
id: 65-starter-set
title: The Starter Set — One Click From Clone to Usable
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [8-model-registry, 9-model-downloads, 35-model-licensing, 34-mask-annotators]
relates: [56-sidecar-bundling, 58-installers, 23-admin-tab]
source_files:
  - backend/app/ml/registry.py
  - backend/app/api/v1/models.py
  - apps/frontend/src/api/models.ts
  - apps/frontend/src/components/StarterSetPanel.tsx
  - apps/frontend/src/components/AnnotatorReadiness.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/models
  - GET /api/v1/annotators
models: [dinov2-small, rf-detr-nano, grounding-dino-tiny, sam2.1-hiera-small, depth-anything-v2-small]
test_files:
  - backend/tests/test_registry.py
  - apps/frontend/src/components/StarterSetPanel.test.tsx
  - apps/frontend/src/components/AnnotatorReadiness.test.tsx
data_flow: reads-existing
last_synced: 2026-08-26
status: complete
phase: all
mdd_version: 11
tags: [onboarding, models, downloads, admin, grounded-sam, first-run]
path: Admin/Models
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 65 — The Starter Set

## Purpose

Reported after a fresh clone on a second machine: *"there are no preinstalled pretrained
heads or RF-DETR and Grounding DINO, Grounded SAM, or Depth Anything"*, plus *"Grounded SAM
does not appear anything for the user to install"*.

Two different problems wearing the same clothes. One is a size fact that cannot be fixed.
The other is a naming bug that was hiding in plain sight.

## Why nothing can be preinstalled

The set a first run actually needs weighs **1,129 MB**:

| Model | Size | Why it is in the set |
|---|---:|---|
| `grounding-dino-tiny` | 658 MB | half of Grounded SAM |
| `sam2.1-hiera-small` | 176 MB | the other half |
| `rf-detr-nano` | 116 MB | the general detector, and the one to fine-tune |
| `depth-anything-v2-small` | 95 MB | depth |
| `dinov2-small` | 84 MB | the backbone every trained head runs on |

Three reasons that cannot go in the clone, any one of which is sufficient:

1. **It is bigger than the product.** Doc 56 measured the packaged installer at 181–377 MB.
   A gigabyte of weights in git makes the repository several times the size of the app, and
   git stores every version of every binary forever.
2. **`CLAUDE.md` forbids it** — "never commit weights, checkpoints, or datasets" — and doc
   35 exists because a weight file carries a licence that has to be *accepted*, not
   inherited by whoever cloned a repo.
3. **Some of it may not be redistributed at all.** The gated models need a HuggingFace token
   and, for SAM 3, an access request Meta approves by hand. Shipping a copy would be
   precisely the thing the gate is there to prevent.

The DINOv2 heads *are* small — 0.7–3.1 MB each, about 6 MB for all of them — but they are
useless without the 84 MB backbone they run on, so they do not change the arithmetic.

**So the target was never zero clicks. It is one.** The work is not making the download
smaller; it is removing the part where someone new looks at fifteen models and has to work
out which five matter and in what order.

## What the button does

`starter: bool` on `ModelSpec`, set on those five. The panel filters the catalogue on it.

**The set lives in the catalogue, not in the panel.** "What does a new user need" is
answered once, next to the models, and reaches the UI through the `/models` DTO — so the
API and the UI cannot hold different opinions, and a test can assert the set by id.

Three decisions inside it that are not obvious:

**Sequential, not parallel.** Five simultaneous HuggingFace pulls saturate the link and make
every progress figure lie about its own speed — five bars all crawling, none finishing. One
at a time is slower to first completion and honest the whole way through.

**The size is on the button, before the click.** `Download all 5 (1.1 GB)`. A gigabyte is a
real decision on a tether or a metered connection, and saying so afterwards is not saying
so.

**Nothing gated is in the set.** Not a size judgement: a gated model needs a token and
possibly a manual approval, so including one turns "download all" into a run that stops
partway with a 409 nobody was expecting. The set is exactly what one click can actually
deliver.

Every entry is the smallest of its family (`-small`, `-nano`). This is the set that makes
the app *work*, not the set that makes it good; base and large are one row up in the list.

### When the total is unknown

HuggingFace does not always send a content length. `downloaded_bytes / total_bytes` with a
zero denominator renders as a confident `NaN%` or a bar pinned at 0% — both of which read as
a stall, which is the one thing a working download must never look like. With no total, the
panel shows megabytes fetched instead.

## Grounded SAM was never missing — its name was

The second report is a real defect and a small one. **Grounded SAM is not a model.** It is
`grounding-dino-tiny` finding the thing and `sam2.1-hiera-small` outlining it, chained. Admin
lists *models*, so those two appeared under their own names, in two different family
sections, with nothing saying what they add up to. Every other tab in the app calls the
pipeline "Grounded SAM". The one screen where you install it was the only screen that did
not.

The backend already knew all of this: `GET /annotators` reports `ready` and
`missing_model_ids` per annotator, and it was being used in the Dataset Generator and
nowhere else. `AnnotatorReadiness` is that endpoint, rendered where installing happens.

**It names the parts rather than offering its own download button.** They are in the list
directly above, each with its own licence to read first, and doc 35 is about that licence
being read rather than clicked past. Readiness comes from the server, too — a second opinion
computed in the component is a second thing to keep in sync, and it would disagree the first
time a pipeline gains a part.

## Tests

The interesting ones are about honesty rather than rendering:

- the set is pinned **by id**, so a sixth model cannot join a 1.1 GB download because
  someone typed `starter=True` while adding something unrelated
- Grounded SAM is starter *as a whole or not at all* — marking one half downloads 658 MB and
  still leaves concept segmentation unavailable, which is the half-installed state this
  whole feature exists to remove
- nothing in the set is gated
- downloads start **one at a time**: `b` has not begun while `a` is still in flight
- a missing `total_bytes` shows megabytes, not `NaN%`
- the readiness panel disappears rather than taking the model list down with it — it is a
  convenience on a tab whose actual job is installing models

## Known limits

The starter set is a judgement about a typical first run, not about any particular user.
Someone who only wants depth still downloads 1.1 GB if they press the button — the
per-model rows below it remain the precise path, and always were.

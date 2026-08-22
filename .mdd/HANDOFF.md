# Handoff — start here

**This is the current handoff and always is.** It is rewritten in place at the end of each
wave rather than appended to. `HANDOFF-wave-2.md` is an older per-wave one kept as history;
do not read it for current state.

**Last updated:** 2026-08-21, after **Wave 7.5** was built and demonstrated. Waves 4–7.5 are
all complete and unmerged. **Only Wave 8 (Packaging) and Wave 9 (Website) remain.**

---

## Waiting on Jan

**1. Merge six branches. Waves 4–7.5 are all marked complete.** Merging is still yours, and
they stack in this order:

```
dev
 └─ feat/dinotraining-wave-4          Wave 4 features 6-9
     └─ feat/external-dataset-import  doc 31 + the NMS and lost-class fixes
         └─ feat/dinotraining-wave-5  docs 32-34
             └─ feat/dinotraining-wave-6 docs 35-37
                 └─ feat/dinotraining-wave-7 docs 38-40
                     └─ feat/dinotraining-wave-7-5 docs 41-53
```

**2. A Wave 8 licensing decision, parked deliberately.** Both YOLO routes evaluated in Wave
7.5 are **AGPL-3.0** (inherited from Ultralytics, confirmed on PyPI). This is billed as a
sharable, installable desktop app and Wave 8 *is* packaging; distributing AGPL-linked code
obliges releasing the whole app under AGPL. Nothing AGPL is in the tree. The decision is
"do we want a YOLO at the cost of the licence", and it is yours.

**3. Housekeeping — the Library tab now shows you the mess.** That is what it is for, and
opening it for the first time on 2026-08-21 showed **21 datasets, 18 heads, 4 fine-tuned
models**. Notable:

- Three datasets named `i'p`, `;oo` and `l’kl;`, all with zero images, from mistyped fields.
- Two OSDaR23 rail datasets that exist only to prove the temporal-split point
  (`OSDaR23 rail train (temporal)`, `OSDaR23 rail holdout (temporal)`); the third,
  `OSDaR23 rail (rgb_center, tiled)`, is the full 392-tile one.
- Four chess heads and several thermal scratch datasets from verification runs.

**Deleting from your store is your call, so I left every one of it.** The imported datasets
(Thermal dogs and people, Blood cells, Chess pieces) and the OSDaR23 tiled set are
deliverables — keep those. Also on disk outside the store: `~/Downloads/osdar23` (652 MB of
RGB frames) and `~/Downloads/osdar23-coco` + `osdar23-split` (~190 MB of tiles). Free disk
was 13 GB when this was written.

---

## What Wave 7.5 turned out to be

It was planned as "General Object Detection" and grew a second half. Thirteen features:

| | |
|---|---|
| 41–44 | RF-DETR as a foundation detector, everywhere; the localisation fixes; fine-tuning |
| 45–46 | Grounded SAM beyond the Generator; the Generator's missing file picker |
| 47–49 | Box review rework; the dataset-format guide; OSDaR23 (OpenLABEL + tiling) |
| 50–53 | A dataset as an image source; the Library tab; the dataset filter; prescan |

**One planned feature was scrapped**: `general-detection-head` (train `dense-detector` on
COCO val2017). Its own plan had conceded the case, and doc 44 removed the last reason to
want it — a fine-tuned RF-DETR reaches mAP 0.800 where the trained head reaches 0.587.

## The three results worth carrying forward

**1. A frozen backbone with a light head has a real ceiling, and OSDaR23 found it.** On
temporally held-out rail frames: trained head **0.339 mAP**, fine-tuned RF-DETR **0.857**.
Doc 44 had measured *identical* mAP@50 on thermal (0.818 vs 0.817) — both found the objects
equally well and only placement differed. On rail it is **0.979 against 0.399**: the head is
not misplacing these objects, it is missing them. 10 px far-field objects on cluttered
natural background is where DINOv2 patch features alone stop separating signal from
vegetation. Reach for a fine-tune there, not a head.

**2. A random image split is wrong for video, and the job runner does not know it.**
OSDaR23 is 10 Hz; consecutive frames differ by **0.4 of 255**. A random split put
near-identical twins in both halves and inflated the reported mAP by **42% for the head**
and **10% for the detector**. Doc 11's rule was "split by image, not by box"; video needs it
one level up — by *segment*. Splitting by contiguous frames was done by hand for doc 49.
**Nothing in the app offers it**, and any dataset whose file names carry frame indices will
hit this.

**3. Tiling is arithmetic, not a technique.** A 10.7 px object in a 2464 px frame arrives at
a 448 px input as **1.9 px** — below the 7 px stride the detector predicts on. No loss
function and no number of epochs recovers an object smaller than one cell. `tiling.py` and
`tiling_images.py` are general: any COCO document with known frame dimensions can be
retiled. **There is no inference-side counterpart** — a head trained on 472 px tiles will
find nothing on a full frame.

---

## Known gaps left open, in the order they will bite

1. **No tiled inference** (doc 49). The rail head is unusable on full frames until this
   exists. The largest single gap in the wave.
2. **Prescan is one shared runner** across the Studio and the Generator (doc 53), so a scan
   in one queues behind a scan in the other and neither says so.
3. **Renaming** is missing from the Library (doc 51) — it needs routes that do not exist and
   a rule about what a rename does to provenance recorded *inside* trained heads.
4. **Per-class rename** is missing from box review (doc 47). Thirty boxes proposed as
   `person` need thirty edits to become `pedestrian`.
5. **`FoundationInfo` does not expose `dataset_ids`** (doc 52), so the dataset filter cannot
   reach fine-tuned models — only heads.
6. **Fine-tunes are 115 MB each** (doc 44) because `save_pretrained` writes the whole model.
   Four of them are in your store. Relevant to Wave 8's installer size.

---

## If you are picking this up cold

Read in this order: `.mdd/.startup.md` for the map, then
`.mdd/waves/dinotraining-wave-7-5.md`, then docs **49** (the hardest data problem in the
project) and **44** (why fine-tuning exists at all). Everything else is reachable from
`.startup.md`.

**MDD hashes** must be recomputed after any initiative/wave edit:

```bash
f=.mdd/waves/dinotraining-wave-7-5.md
new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
perl -pi -e "s/^hash: .*/hash: $new/" "$f"
```

**Gates**, all green as of 2026-08-21: `1133` backend tests, `519` frontend, `ruff` +
`mypy` + `tsc` clean, no file over 300 lines.

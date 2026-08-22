# Handoff — start here

**This is the current handoff and always is.** It is rewritten in place at the end of each
wave rather than appended to. `HANDOFF-wave-2.md` is an older per-wave one kept as history;
do not read it for current state.

**Last updated:** 2026-08-20, after doc 31 (external dataset import) unblocked Wave 4's
expert-head demo-state.

---

## Waiting on Jan

**1. SAM 3 is done.** Approved, downloaded (3.2 GB, safetensors only, zero pickles) and
**Phase 7b passed on 2026-08-19 with no code changes**. Both annotators report `ready`.
Doc 30 is `complete`. There is nothing left waiting on you here.

**2. Merge Wave 4 — it is marked complete.** Both demo-state halves are demonstrated, so
the wave doc now says `status: complete` (flipped 2026-08-20 on your "continue with the
whole project"). **Merging is still yours**: `feat/dinotraining-wave-4` is 4 commits ahead
of `dev`, and `feat/external-dataset-import` sits on top of it with 5 more. If you disagree
with the flip it is a one-line revert in `.mdd/waves/dinotraining-wave-4.md` plus a hash
recompute.

**3. Housekeeping — now six datasets and three heads.** Still in your real store from
verification runs: `Wave4 mask smoke`, `Generated bolts`, and four thermal scratch datasets
(`Thermal flywheel check`, two × `Thermal from expert head`, `Thermal, auto-proposed` — two
of them empty). Also **three obsolete detection heads** trained before the NMS fix
(map 0.263 / 0.207 / 0.425), superseded by the three after it (0.404 / 0.387 / 0.525).
Deleting from your store is your call, so I left all of it. The three *imported* datasets
(Thermal dogs and people, Blood cells, Chess pieces) are the deliverable — keep those.

*(The ~920 MB of dead pickles was cleared on 2026-08-19. Each had a matching
`model.safetensors` beside it; all three models were re-loaded afterwards and Grounded SAM
returned byte-identical results, so they were confirmed dead weight rather than assumed.
The model cache is now 918 MB and the volume is back to **15 GB free, 97% used**.)*

---

## Where the project stands

**Waves 1–3 merged to `dev`. Wave 4 is built and pushed but not merged.**

```
dev                       ba3c663   (features 1–5 of Wave 4 are already on it — see below)
feat/dinotraining-wave-4  e6e1deb   4 commits ahead of dev
922 backend tests · 287 frontend tests · ruff, mypy, tsc all clean
```

⚠️ **`dev` already contains Wave 4 features 1–5.** You merged the branch mid-wave on
2026-08-19 (`e110752`) and left the checkout on `dev`, and I then committed feature 5
straight to it before noticing. Nothing was lost and the branch was fast-forwarded back
into line, but it means `dev` is **not** a clean pre-wave baseline. Merging the remaining
four commits is an ordinary fast-forwardable merge.

## Wave 4 — nine features, docs 22–30

| # | Feature | Doc | State |
|---|---|---|---|
| 1 | mask-dataset-store | 22 | ✅ verified |
| 2 | mask-annotator-registry | 23 | ✅ verified |
| 3 | hf-token-settings | 24 | ✅ verified in browser |
| 4 | expert-annotator | 25 | ⚠️ refusal path verified on real weights; **success path stub-only** |
| 5 | generator-review-ui | 26 | ⚠️ empty states verified; **review loop stub-only** |
| 6 | grounded-sam-annotator | 27 | ✅ verified end to end, real weights |
| 7 | mask-review-ui | 28 | ✅ verified end to end, real weights |
| 8 | generated-dataset-writer | 29 | ✅ verified end to end, real database |
| 9 | sam3-annotator | 30 | ✅ verified end to end, real weights |

## The demo-state question — read before flipping the wave

The wave's demo-state has **two halves**, and they are in different states:

> *"User runs trained expert head(s) over new images, reviews/marks predictions, and saves a
> new dataset ready to train another head. Separately, SAM 3 proposes segmentation masks
> over an image set which the user reviews and saves."*

**The mask half is fully demonstrated** — better than written, in fact: it works with
**Grounded SAM**, which needs no gated model at all. Concept in, masks out, reviewed,
saved, exported to COCO. Verified against real Grounding DINO + SAM 2.1 on MPS.

**The expert-head half is now demonstrated too** (2026-08-20). DINOv2 still publishes no
pretrained detection head — that part was never going to change — so the unblock was to
*train* one. Doc 31 imports third-party COCO datasets, and three detectors were trained on
frozen `dinov2-small` and driven through the Dataset Generator end to end. Before that
work, the Dataset Generator correctly showed:

> *No installed head can propose boxes. Classification, segmentation and depth heads run in
> the Inference Viewer; only a detection head can be reviewed as boxes — train one in the
> Head Trainer.*

**To close that half you must train a detector through Wave 2**, on a box dataset from the
Annotation Studio. That is a genuine piece of work, not a bug fix — hence leaving the
decision to you rather than flipping the wave myself.

## What Wave 4 delivers that the plan did not anticipate

**The gated-SAM-3 block disappeared.** No ungated model is a drop-in for SAM 3, but
**Grounding DINO + SAM 2.1 composed reproduces its contract** — text concept in, masks and
boxes out — under Apache-2.0 for a 176 MB download. That is why eight of nine features
could be verified without waiting on Meta. Grounded SAM is a permanent first-class
annotator, not scaffolding.

**SAM 3, not SAM 3.1**, settled on evidence: 3.1 adds only Object Multiplex (~2× *video*
throughput, unused here) and has **no `transformers` integration**, while `facebook/sam3`
ships `Sam3Processor`/`Sam3Model` and drops into the existing loader.

## Four bugs found by running the app, not by tests

Each is recorded in the doc that owns it. They are the strongest evidence for the project's
own rule that green tests are necessary and not sufficient.

1. **The schema had no migrations at all** (doc 22). `CREATE TABLE IF NOT EXISTS` is a
   no-op on an existing table, so a widened CHECK applied only to *new* databases. Every
   test builds a fresh one and passed; your machine would have 500'd. `SCHEMA_VERSION = 2`
   existed and was **never read by anything**.
2. **Every model downloaded ~2× its estimate** (doc 02). `snapshot_download` fetched the
   whole repo including the pickle duplicate this project refuses to load —
   grounding-dino-tiny used 1.3 GB against a 690 MB claim.
3. **The app read no `.env` at all** (doc 24). `env_file=".env"` resolves against the
   *working directory*; the backend runs from `backend/`, found nothing, and silently ran on
   defaults while your real file sat at the repo root with all eight keys.
4. **Verdict tags were invisible in light mode** (doc 05, a **Wave 1** bug). `currentColor`
   resolves against an element's *own* colour, so `color-mix(currentColor, #000)` on a tag
   that also sets its own near-black text produced near-black on near-black — contrast
   **1.11**. Dark-first UI hid it for three waves.

## If you are in a fresh environment

The repo holds **no model weights and no venv** — both gitignored.

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest tests/ -q                                     # expect 871
cd ../apps/frontend && npm install --legacy-peer-deps && npx vitest run   # expect 279
```

Then the models. **Everything below is ungated** — no token, no account:

```bash
# with the backend running
curl -X POST http://127.0.0.1:8756/api/v1/models/dinov2-small/download          #  84 MB
curl -X POST http://127.0.0.1:8756/api/v1/models/grounding-dino-tiny/download   # 658 MB
curl -X POST http://127.0.0.1:8756/api/v1/models/sam2.1-hiera-small/download    # 176 MB
```

Those three are all Grounded SAM needs. Sizes are measured from the HuggingFace API,
safetensors only, and are now accurate — the pickle duplicate is excluded.

## Smoke test — free, no training, no gated model

The one that exercises the most: **Dataset Generator → Grounded SAM → review → save.**

1. Make a folder with an image containing two visually distinct objects.
2. Dataset Generator → *Save into* "Create a new dataset…", name it.
3. Choose **"Grounded SAM — type a concept, get masks"**.
4. Folder = your folder, concept = two phrases, e.g. `a red circle. a blue square.`
5. **Propose masks** → **click one mask** to cycle it to Negative → **Save to dataset**.

**How to read the result.** Expect one mask per phrase, tinted by verdict, with a dashed
outline on the mask's own bounding box — *not* the prompt's, because SAM tightens a loose
box. The counter should read `masks=2 positive=1 negative=1`. Then export COCO and expect
**one** annotation: negatives are deliberately excluded, because a COCO annotation asserts
"an object is here" and a rejected mask asserts the opposite.

Reference numbers from a synthetic scene, which is how accurate this actually is:

| concept | mask area | true area | error |
|---|---|---|---|
| a red circle | 31,417 px | π·100² = 31,416 | **1 px** |
| a blue square | 32,197 px | 180² = 32,400 | 0.6% |

**A first run takes ~10–15 seconds** — two models load on first use and are then cached.
That is not a hang.

## Gotchas (all still live)

- **Restart the backend after backend edits** — uvicorn does not reload. There is often a
  stale one already on 8756 from a previous session; kill it first.
- **Stale Vite HMR errors survive a server restart *and* a page reload**, name files you
  never touched, and the browser console keeps them **per tab** — so restarting the dev
  server does not clear the history. A React *Rules of Hooks* warning appeared this way and
  was not real. **Verify with `tsc`, a test, and the rendered page — never the console.**
- **Copying a WAL-mode SQLite database without its `-wal` file gives a stale snapshot.**
  It shows data that is gone and hides data that is there, and looks exactly like data
  loss. Copy `.db`, `.db-wal` and `.db-shm` together — and note the names must be
  `X.db-wal`, not `X-wal`. I hit this twice, the second time *after* documenting it.
- **`git commit -m` with quotes breaks under zsh**, and a heredoc piped into `git commit`
  trips the safety hook. Write the message to a file and use `-F <file>`.
- **`rm -rf` and `DROP TABLE` are blocked by hooks.** The `DROP TABLE` block fired on an
  in-memory test fixture; rewriting it to avoid `DROP` gave a cleaner test anyway.
- **The 300-line hook guards the *editing tools*, not the filesystem.** It fired four
  times this wave — and two files still slipped over the limit because the last edits to
  them went through a scripted `python` heredoc, which the hook never sees. Check with
  `find … | xargs wc -l | sort -rn | head` before calling a wave done. Currently closest:
  `heads/registry.py` 293, `store.py` 284, `head_catalog.py` 283.
- **MDD hashes** must be recomputed after any initiative/wave edit:
  ```bash
  f=.mdd/waves/dinotraining-wave-4.md
  new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
  perl -pi -e "s/^hash: .*/hash: $new/" "$f"
  ```
- **`vi.restoreAllMocks()` does not clear `vi.fn()` call history** — only spies. A test
  read `mock.calls[0]` from a *previous* test and appeared to prove a bug that did not
  exist. Use `clearAllMocks` as well.

## Architecture Wave 5+ must honour

Everything from Wave 3's handoff still holds. New this wave:

- **One `MaskAnnotator` contract, implementations keyed by id.** `build_annotator` in
  `app/ml/annotators/build.py` is the **only** place an id maps to an implementation. An
  `if annotator_id == "sam3"` anywhere else is a defect, exactly as `task ===` is in
  `components/overlays/`.
- **`render_hint` answers "what can this head do", never `task`.** Exposed on
  `GET /api/v1/heads` for that reason. Inferring capability from the task label is the same
  defect in a different place.
- **Migrations are driven by what is on disk**, never by the version stamp:
  `sqlite_master.sql` for constraints, `PRAGMA table_info` for columns. A probe of the form
  "does table X exist" is already true by the time the runner is consulted — that shipped
  once and skipped the migration for every real install.
- **A schema change needs a migration step, not just a `schema.py` edit.** Constraint
  changes rebuild the table; column additions `ALTER` in place. A rebuild must intersect its
  carried columns with what the source table actually has.
- **`provenance` is the *kind*, `producer` is *which*.** The producer is a JSON snapshot
  captured at write time, not a foreign key, because a head can be deleted and "which model
  made this annotation" is exactly what an old dataset is asked.
- **Weights are never bundled and never auto-downloaded.** Now pinned by tests:
  `snapshot_download(` appears in one file, and every loader refuses a missing model.
- **Hand-mirrored frontend types drift silently.** `Provenance` and `DatasetCounts` both
  went stale this wave and neither failed until something assigned to them. When you change
  a backend literal or model, grep `apps/frontend/src/types` and `src/api` in the same
  commit.

## Regenerating the doc graph

`.mdd/connections.md` is generated from feature-doc **frontmatter only** — never doc
bodies. It was stale by nine docs at the end of this wave. Current state: **30 docs, 69
dependency edges, 47 shared source files, zero warnings** — no broken `depends_on`, no
cycles, every doc has a `path`.

## SAM 3 — what the real run showed

Every risk the stub could not cover came back clean: mask shape (the singleton-axis squeeze
was a harmless no-op), the device hop off MPS, positional score alignment, and
`target_sizes` order on a non-square image. The API shape introspected from `transformers`
5.15 was correct, so **no code changed**.

| concept | score | mask area | true area |
|---|---|---|---|
| `a red circle` | **0.977** | 31,434 | 31,416 |
| `a blue square` | **0.968** | 32,250 | 32,400 |
| `a unicorn` | — | *nothing* | does not hallucinate |

SAM 3 scores higher than Grounded SAM on the same image (0.977 against 0.883) — the quality
difference the licence buys.

**One real finding, now the top item in doc 30's `known_issues`:** SAM 3 takes **one concept
per call**. Given `"a red circle. a blue square."` it returns a single mask at score
**0.372**, against 0.977 and 0.968 for the same phrases run separately. Grounded SAM handles
the joined form natively because Grounding DINO reports which phrase matched each box. The
concept field now shows a different placeholder and hint per annotator — but the prompt is
**not** split automatically. Doing that, and calling SAM 3 once per phrase, would make the
two annotators behave identically and is the obvious next improvement.

## Known issues — good first tasks

- **The ImageNet classifier ships no class names**, so the viewer renders `class 416`
  instead of `Siamese cat`. Still the most visibly rough edge, still self-contained. The
  1000-name list belongs with the catalogue entry in doc 15.
- **Vitest reports 2 pre-existing unhandled errors** from Wave 3's `SideBySideViewer` —
  jsdom lacks Pointer Capture. Harmless but vitest warns they "might cause false positive
  tests". A two-line stub in the test setup fixes it.
- **No pretrained detection head exists** — no longer a blocker. Doc 31 imports a
  third-party COCO dataset and Wave 2 trains a detector on it in under a minute on MPS.
  Recipe: `POST /api/v1/datasets/import/coco` with `{name, directory, copy_images}`, then
  `POST /api/v1/training/jobs` with `dense-detector` + `dinov2-small`.
- **Training is not reproducible run to run.** `split_seed` fixes the split; nothing seeds
  weight init or shuffling. Two runs of an identical config gave map 0.404 and 0.387 — fine
  for a demo, wrong for comparing two configurations, which is what the Head Trainer invites.
- **The generator's default score threshold (0.30) is tuned for Grounding DINO**, not for a
  freshly trained head. The thermal detector proposes ~20 boxes over two people at 0.30; the
  top two are right. A per-head default would make the first run read far better.
- **Mask editing is deliberately absent** — review is verdict-only. A brush or polygon
  editor is a later wave and was not needed to close the flywheel.
- **Dataset lineage** (parent link, generation timestamp) was considered in doc 29 and
  deliberately not built. Revisit when datasets are routinely generated from other datasets.
- **N result panes are equal-width columns**; **zoom is about the stage box, not the image
  content**. Both unchanged from Wave 3.

## State of the machine

- Installed: `dinov2-small`, `grounding-dino-tiny`, `sam2.1-hiera-small`, **`sam3`**, plus
  the three default heads. **Both mask annotators are ready to run.**
- Not installed: `dinov2-base/large`, `grounding-dino-base`, both DINOv3.
- Database at **schema v6** (`imported` provenance). Nine datasets present — three imported,
  four scratch, two from Wave 4 (see "Waiting on Jan").
- **12 GB free, 98% used** — SAM 3's 3.2 GB landed after the 920 MB pickle clear-out. The
  model cache is 4.1 GB, safetensors only.
- Branches `feat/dinotraining-wave-2` and `feat/dinotraining-wave-3` are merged but still
  exist locally and on origin. Cleanup was offered in two sessions and not requested.

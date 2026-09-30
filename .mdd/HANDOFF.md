# Handoff — start here

**This is the current handoff and always is.** It is rewritten in place at the end of each
wave rather than appended to. `HANDOFF-wave-2.md` is an older per-wave one kept as history;
do not read it for current state.

**Last updated:** 2026-09-30, at the end of the **Wave 15.6 build**.
- **Waves 1–12:** in `dev` and `main`.
- **Waves 13, 14, 15, 15.5 and 15.6** (docs 99–124): in `dev` (15.6 as `d74a1a1`),
  waiting for Jan's test. Each status stays `in_progress` until Jan confirms its
  demo-state.

**Next:** Wave 16, the website.

---

## Wave 15.6 — MLOps: model cards, export, ONNX, MLflow (2026-09-30)

Jan: "Trained models should be exportable … and an interface for MLOps tools, e.g.
MLflow" — before the website.

| | |
|---|---|
| 120 | **Model card:** base, head and module, classes in order, the exact preprocessing, decode, metrics, datasets and recipe, per-epoch history (persisted from now on), weights with SHA-256. `GET /cards/{kind}/{id}`; MCP `get_model_card`. |
| 121 | **Export zip:** card, weights, `dino_runtime.py` assembled from the app's own source (parity-tested per head type), `predict.py`, pinned requirements, README. Library: Export and Show where it is. |
| 122 | **ONNX:** backbone and head as one graph, dynamic batch, parity checked at export (refused above 1e-3). An optional `[export]` extra. |
| 123 | **MLflow tracking** over REST (checked against a real MLflow 3): a run per training with params, tags, per-epoch metrics, card and bundle, and a registry version. Never at training's cost. Admin → Connection → MLflow. |
| 124 | **Backfill:** "Send existing models to MLflow", each model once. |

- **Proof, live:**
  - A real DINOv2 detector head was exported and run outside the app: the same 12 boxes
    as `/inference`, 0.0 px apart.
  - Its ONNX file matched PyTorch within 4.4e-5 px.
  - A 3-epoch head appeared in MLflow with curves, artifacts and version 1.
  - The real library was backfilled: 25 of 30 sent, a second press sent 0.
- **Found live and fixed:**
  - MLflow refuses ':' in model names.
  - A failed registration left the run RUNNING.
  - The MLflow docs give the wrong registry path.
  - A SAM card claimed "backbone not installed".
- **Clean-up:** the two test heads were deleted, MLflow was disconnected in `.env`, and the
  scratch MLflow server was stopped.
- **To try it:** `pip install mlflow`, then `mlflow server --port 5001` (on macOS the
  system holds port 5000), then enter `http://127.0.0.1:5001` under Connection → MLflow.

---

## Wave 15.5 — Annotating the normal way (2026-09-30)

From Jan's test of the phrase bar: "when annotating, all objects are marked"; classes
m8 and m9 with "screw" over both.

| | |
|---|---|
| 115 | **Umbrella terms:** a phrase over several classes (`phrase_classes`). SAM 3 asks "screw" with all m8 and m9 outlines, never a negative where a member is present, and skips it where a member is unknown. The API, MCP and recipe carry it; the job note names it. |
| 116 | **Slim phrase bar:** chips, "+ Umbrella term", Manage phrases (variations and look-alikes per class, umbrellas, older sub-phrases), and the help rewritten. The checks are folded for imports, and their keys work only while open. No class is created there. |
| 117 | **Saved means complete:** a picture is known for a class when it was saved after the class existed (`annotated_at >= since`), or when it was checked by hand. This replaces doc 108's checked mode. `/completeness`; the audit finding `saved-before-class`; the Studio stores its prompt's terms as classes. |
| 118 | **New-class question:** a banner for each class with pictures saved before it. "It does not occur there" marks them absent; "Review them later" keeps a reminder. MCP: `get_completeness`, `mark_absent_in_older_pictures`. |
| 119 | **Add-only review:** `CanvasBox.saved`; a re-run keeps saved and hand-drawn annotations and adds no duplicates. "Review for X" filters to the unknown pictures and proposes only X. "No X here →" marks the picture absent. |

- **Demo run** (SAM 3, 1 epoch): mIoU 0.217 → 0.450. The notes name the umbrella and the
  70 pictures left out for the class added later.
- **Found:** a filter that started on the picture already shown hung on "Loading image…".
  The prescan filter had it too. It is fixed, with a regression test.
- **Test data:** "Wave 12 filled-ring convention" is unchanged. The test umbrella, the
  class, the checks and the run's model were all deleted.

---

## Wave 15 — English and German (2026-09-30)

| | |
|---|---|
| 111 | **Framework:** typed catalogues (`src/i18n/en|de/<ns>.ts`); a missing German key is a compile error. `useT()` with `t`/`tp` (plurals via Intl.PluralRules). A language switch in the header, stored as `language`. The API client sends `Accept-Language`. |
| 112 | **Frontend:** about 1 070 keys in 9 namespaces, with a German smoke test per namespace. Hand-written plurals became real ones. |
| 113 | **Backend:** the English stays in the code. An ASGI middleware translates the text fields of `/api/v1` JSON answers for `Accept-Language: de`, using 475 templates. Tests check all 20 audit rules and the four static endpoints; MCP stays English. |
| 114 | **German:** `GLOSSARY.md`, informal "du", one word per concept. |

**Known gaps (doc 113):**
- An audit stored before a rule's wording changed keeps those sentences in English until it
  is re-run.
- Still English: training and video job messages, model and head descriptions, rarer 422
  details, unhandled 500s.
- The model-input examples and the copied AI guide stay English on purpose.

**For Jan:** review the glossary choices listed in doc 114.

**From Jan's test (2026-09-30, same branch):**
- **Technical terms in German are English now** (doc 114, amended).
- **A comma separates search terms** for Grounding DINO and SAM 3, with one term per box
  (doc 105).
- **The Studio:** "← Back to overview", and the session survives other tabs (doc 105).
- **Phrases:**
  - a "belongs to" class choice;
  - look-alikes explained;
  - Delete;
  - no look-alike negative beside a rejected outline (doc 108).

---

## Wave 14 — Annotate for the model (2026-09-30)

| | |
|---|---|
| 103 | **Phrases:** text, class, variants (stored once, expanded at training), look-alikes; outlines linked to phrases; a check per picture and phrase (all marked / not in this picture). Class names are implicit phrases, so there is no migration. |
| 104 | **"What will this dataset train?"** A matrix of targets × layers (required / recommended / optional, each with why) for the Studio and MCP, and a checklist per picture. |
| 105 | **Phrase bar:** chips with counts, keys 1–9, comma variations, the selected outline's phrases, picture checks (A / N), Manage phrases, and "How phrases work". |
| 106 | **Outline editing:** ⊕/⊖ SAM 2 clicks, a brush and an eraser (server-side, exact), undo, Outlines from my boxes. |
| 107 | **Audit per task:** classifier pictures with two classes; outlines in pieces or twice; SAM 3 thin phrases, unchecked pictures, no variations, no negatives. Unused Prepare steps are marked. |
| 108 | **SAM 3 training:** checked pairs only (legacy datasets unchanged), variations, and negatives (cross, generic `num_negatives`, look-alikes, rejected); the job notes its queries. SAM 2 learns clicks. |
| 109 | **Quality:** a guideline per dataset, a second look with a change rate, frame consistency, and *unclear* is never a negative. |
| 110 | **MCP:** six tools, and guide section 2d. |

**Measured:**
- **SAM 2 with click prompts:** 0.804 → **0.955** in one round (Wave 12's box-only
  training took six).
- **SAM 3 fine-tuning improves a model for the first time:** one round at 1e-5 took
  held-out mIoU from 0.434 to **0.603**.
  - At the old default 1e-4 it fell below the base (0.193 on validation; 0.160 without
    generic negatives), and nothing was saved.
  - The SAM 3 default is now 1e-5.

**Found and fixed:**
- **Outline editing:** `CompositedMasks` did not redraw an outline edited in place.
- **Wave 11:** the keep-source split stored no settings, so its recipe was refused (fixed
  in Wave 13).
- **Wave 13:** an MCP test left a prep job reading SQLite, and the suite segfaulted
  intermittently.
- **Settings:** two catalogue keys were missing after a failed text replacement. A test
  now guards against that.

**Gates:** backend 1784 (three clean runs), frontend 1032, tsc, ruff and mypy app.

## Waiting on Jan — Wave 14

1. **Studio, "What will this dataset train?" → SAM 3:**
   - Read the panel.
   - Add a phrase with variations; mark pictures with A / N.
   - Select an outline and try ⊕ / ⊖, brush and undo.
2. **Annotation guideline and Second look.**
3. **Prepare data → Fine-tune SAM 3:** read the audit's phrase findings.
4. **Merge:** if it holds, merge `feat/dinotraining-wave-14` → `dev`.

## Wave 13 — Every training setting explained, default recipes (2026-09-30)

| | |
|---|---|
| 99 | **Parameter catalogue.** One declaration per family (DINO head, RF-DETR, SAM 2.1, SAM 3, DINO backbone): plain name, term, help, default + why, range, basic/advanced. `GET /training/parameters[/{model}]`; fine-tune requests are resolved against it (unknown option or out of range → 422 naming it). Adapter constants became settings with unchanged defaults. |
| 100 | **Parameter form.** "Rounds (epochs)" with a **?** (explanation, default, why; Esc returns focus), Advanced folded with a changed count, reset per field and all, recipe-set fields locked. Only overrides are state, per family. |
| 101 | **Default recipes.** `POST /datasets/{id}/recipes/default` (a job): audit, the leak-free split (kept if made or imported), recommended balance and copies, "Default for <model>", idempotent. Profiles for every trainable model. The "What is a recipe?" card, with Create the default recipe and Open Prepare data. |
| 102 | **Agents.** `get_training_parameters`, `create_default_recipe` (`get_job` kind `default-recipe`), `train_head` `parameters`, `start_finetune` `options` with per-model defaults; the guide updated. |

**Found and fixed while building:**
- **Head `batch_size` (16) was accepted and never read**: every head trained one picture
  per step. It is now honest (gradient accumulation), with default 1, so no result moves.
  `save_best_only` was never honoured either, and is left out of the catalogue.
- **`keep-source` split stored no settings,** so a recipe refused a dataset that was split
  (Wave 11).
- **A cleared number field showed "NaN"** (NaN ≠ NaN in the draft sync).

**Verified live:**
- The ? popovers and Advanced settings for RF-DETR and the DINO head.
- The default recipe on "Wave 11 intake check": the imported split was kept (16/3/1),
  weighted loss, the indoor preset, and the preflight passed.
- Open Prepare data landed at the dataset and model.
- MCP returned the same catalogue, and the same recipe.

**Gates:** backend 1725, frontend 995, ruff, `mypy app` and tsc all clean.

**Not clean, and older than this wave:** `mypy app tests` stops on `head_testkit` being
imported under two module names. With `--explicit-package-bases` it reports about 164 old
typing errors in 40 test files. A background task chip was offered for it.

## Waiting on Jan — Wave 13

1. **Training → DINO head, and Fine-tune a model:**
   - Open a **?**, and read whether the explanations make sense to a non-expert.
   - Change a value, reset it, and open *Advanced settings*.
2. **A dataset without a recipe:**
   - Read the "What is a recipe?" card.
   - Press **Create the default recipe**, and check that it is selected.
   - Try **Open Prepare data**.
3. **Merge:** if it holds, merge `feat/dinotraining-wave-13` → `dev`, and later → `main`.

## Wave 12 — Fine-tuning SAM 2, SAM 3 and DINO backbones (2026-09-30)

| | |
|---|---|
| 92 | **Data-requirements contract.** One source per model for what the data must look like (RF-DETR, SAM 2.1, SAM 3, DINOv2/v3 × task), plus a preflight that names the rule, the numbers and the fix. |
| 93 | **One runner, per-model adapters.** Preflight, the recipe's split, base vs fine-tuned on the same held-out pictures, and **the base model competing as round 0**: a fine-tune that is not better is not saved. |
| 94 | **SAM 2.1.** Trains the mask decoder only (a few MB). Offered as "Grounded SAM · <name>". |
| 95 | **DINO backbones.** The last blocks train with a task head and are saved as a variant with its own id. The baseline is a head on the frozen backbone. |
| 96 | **SAM 3.** Hungarian matching and DETR losses on 15 M of 840 M parameters. Offered as "SAM 3 · <name>". |
| 97 | **UI.** "Fine-tune a model": requirements card, readiness check, before/after. Doc 44's panel is removed. |
| 98 | **Agents.** `get_finetune_requirements`, `check_dataset_for`, `start_finetune`; guide section 4 rewritten. |

**Measured:**

| Model | Data | Base → fine-tuned (held-out) |
|---|---|---|
| RF-DETR nano, 2 rounds | Blood cells, recipe | mAP 0.000 → **0.616** (a DINO head: 0.412) |
| SAM 2.1 small | synthetic shapes it already outlines | mIoU 0.957 → 0.936 (worse; the runner now saves nothing) |
| SAM 2.1 small | filled-ring convention | mIoU 0.804 → **0.957** |
| DINOv2-small, 4 blocks | filled-ring convention | head on frozen 0.849 → variant **0.869** |
| SAM 3 | filled-ring convention | base **0.434**; a full run was cancelled (memory shared with NinaNatur's 19 GB process) — see doc 96 |

**Carry forward:**
- **Fine-tuning teaches your outlines, not what a model already does.** It made SAM 2
  worse on easy shapes. That is why the base model competes and why both numbers are
  always reported.
- **Memory is a budget, not a constant** (doc 96). A fixed 3 GB feature cache next to
  SAM 3 swapped this 16 GB Mac (24.5 GB of swap), and an epoch could not even be
  cancelled. Caches are now a share of physical memory, and cancelling is checked between
  pictures.
- **The old headline numbers were random-split numbers:** RF-DETR 0.96 against a head's
  0.5–0.6 on rail. On a leak-free split, Blood cells give 0.62 against 0.41. The rail
  comparison deserves a re-run with a recipe.
- **DINOv3 was not run here.** It is gated, and downloading needs Jan's go-ahead. The code
  path was verified with DINOv2-small.
- **Synthetic data only for SAM.** The app holds no real instance-mask set of useful size.

## Waiting on Jan — Wave 12

- **See the demo-state:** Training → Fine-tune a model → SAM 2.1 on a dataset with masks
  and a recipe. Read the card, fix what the check says, train, and compare before/after.
- **Run SAM 3 once on a free machine** (doc 96): Training → Fine-tune a model → SAM 3 on
  "Wave 12 filled-ring convention" with its recipe, 2 rounds. It is the one fine-tune not
  yet seen to completion.
- **Allow the DINOv3 download** if DINOv3 fine-tuning should be verified on real weights
  (327 MB; gated, so the token must be set).
- **Test data from this wave:** datasets "Wave 12 synthetic outlines" and "Wave 12
  filled-ring convention", and fine-tuned instances (RF-DETR "blood rf-detr (wave 12
  runner)", "outlines SAM" (the worse one, saved before the round-0 rule), "filled-ring
  SAM", "rings DINOv2 variant", and SAM 3's), to delete in Library.

## Wave 10 — Look & Feel (2026-09-29), on its own branch

The Pixabay "octagon" particles clip, mirror-stitched into a seamless 58 s loop (4.0 MB,
H.264, provenance and licence recorded), as the app's background. It pauses when hidden and
shows the poster for reduced motion or when switched off (Admin → Appearance). Also:
- NinaNatur's Draft Sketch outline on every button;
- Lato, bundled rather than fetched;
- contrast measured against the loop's brightest frame, with tokens fixed where they
  failed AA.

Docs 76–80 are on `feat/dinotraining-wave-10`. Its status stays `in_progress` until the
packaged app has been seen: `tauri dev` does not apply the packaged CSP (`media-src 'self'`
was added), and WebKit plays video differently.

## Wave 11 — Guided Data Preparation (2026-09-29/30)

Jan's "most important and most complex wave": preprocessing done for people who have
never trained a model, most of all for external data. It is all in a new tab, **Prepare
data**, between Annotation Studio and Training, and in the API and MCP for agents.

| | |
|---|---|
| 81 | **Audit.** Plain-language findings (what / why / what to do, example thumbnails), judged at the target model's input. |
| 82 | **Import check.** Detects xywh / xyxy / normalised boxes. An unchecked xyxy export had lost 162 of 273 boxes silently. |
| 83 | **Safe fixes.** Exclude and include, never delete; a class map that renames, merges or leaves out. Undoable. |
| 84 | **Leak-free split.** Scenes and video stretches never straddle sides; buffers at contiguous boundaries; stored and seeded. |
| 85 | **What the model sees.** Fit, object sizes at the input, the tiling decision, and the real pictures at the model's resolution. Found: RF-DETR and SAM 2 *stretch* to a square, they do not letterbox. |
| 86 | **Unequal classes.** Weighted loss or repeat-factor sampling, recommended from the numbers. |
| 87 | **Augmentation presets.** Geometry-safe (property-tested), with a whole-word meaning guard (no mirroring for signs, text or sides). |
| 88 | **Recipe.** A versioned, never-edited snapshot. It says when the data no longer matches it. |
| 89 | **The Prepare data tab.** Seven steps, each with a recommended default and why. |
| 90 | **Training uses the recipe.** Stored split, tiles, strategy, augmentation. Fixes apply to every run. A **test score** is reported and saved with the head. |
| 91 | **For agents.** Eight MCP tools and guide section 2c, "prepare before you train". |

**Found live, and worth carrying forward:**
- **The shared SQLite connection was used by several threads at once** (doc 03, Bugs).
  Symptoms: "API misuse" 500s, a false "Dataset not found", and one thread's commit
  persisting another's half-done work. Latent since Wave 1. `transaction()` now holds a
  lock.
- **Every MCP tool's error explanation was lost** (doc 91). `ApiError` was not a
  `ToolError`, so the model saw only "Error executing tool".
- **mAP counted classes absent from the evaluation side as 0** (doc 11, Bugs). With a
  leak-free split that is common, and it cut scores by a third per missing class.
- **The first honest numbers are lower.** Blood cells: validation mAP 0.498, **test 0.412**.
  On OSDaR the leak-free split leaves only 58 groups, and a DINOv2-small head learns little
  in 6 epochs, tiled or not (doc 90). RF-DETR's 0.96 from Wave 7 was measured on a random
  split, so treat it with the same caution until it is re-run with a recipe.
- **Balance strategies could not be told apart** on Blood cells with one seed and 8
  epochs (doc 86). The recommendation rule is reasoned, not yet measured.

## Waiting on Jan — Waves 10 and 11

**A. Merge order.** Both branches start from `dev` at `24f5230`. Wave 11's new tab uses
only colour tokens both branches define, so either order works. Wave 10 first gives Wave 11
its look; check the Prepare data tab once both are in.

**B. See Wave 11's demo-state yourself** (`./scripts/dev.sh web`):
1. Prepare data → a dataset and a model.
2. Run the audit and read the findings.
3. Split, then "What the model sees", then save a recipe.
4. "Train with …" opens Training with the recipe chosen; the finished run shows a test
   score.

**C. Not seen in WebKit.** The Prepare tab draws `<img>` data URLs and a
`image-rendering: pixelated` preview, with no canvas data. That is low risk, but it is not
evidence.

**D. Tasks offered out of scope**, still open: blocking file IO on the event loop
(macOS's ~/Downloads prompt stalled a preview for 6,711 s), doc 68's path-confinement
claim, and unhandled `setPointerCapture` errors in the viewer tests.

**E. Test data left behind:** recipes on Blood cells ("blood v1") and OSDaR ("osdar
tiled", "osdar whole"), and new heads from the comparison runs, for deleting in Library.

---

## Wave 9 — what was built (2026-09-29)

Inserted ahead of the website wave at Jan's request, **by renumbering** (9 → 10, 40
references). Every feature was verified in the running app: web mode, with real Grounding
DINO and RF-DETR weights.

| | |
|---|---|
| 69 | **Remembered entries.** Every path, name, prompt and model choice survives a tab switch and a restart (`localStorage`, guarded reads, `stillListed` for ids that may be gone). The HF token draft is deliberately excluded. |
| 70 | **Generator action bar.** *auto* boxes beside Propose and Save (on by default), with everything beside Previous/Next. Auto-save fires on *leaving* an image. The session remembers what it saved, so going back shows it. |
| 71 | **Autoplay.** Propose → hold 0.5 s → save → next, from the current image, stoppable at any point without saving the image it stops on. *Hidden* mode shows only a percentage. |
| 72 | **Ask when unclear.** A user-set score band pauses autoplay and marks those proposals *unclear*. Continue saves the user's verdict. |
| 73 | **A video as the Generator's source.** The chosen range is decoded to JPEGs inside the dataset (a polled job), and every save records `sequence` + `frame_index` (schema **v8**). |
| 74 | **Inspect datasets tab.** Plays a dataset's videos, folders and loose images with the stored annotations, coloured by class. The Generator jumps there with the dataset open. Frames never saved (nothing found) are merged back from disk, so playback keeps real time. |
| 75 | **Annotation timeline.** One coloured bar per class under the player. Click a bar to select its class, then ⇤ First / ◀ Previous / Next ▶. |

**Pre-existing bugs found and fixed on the way:**
- **Grounding DINO could not propose in the Generator or the Studio.** Doc 66 offered it,
  and `propose_foundation_boxes` refused it with "does not predict boxes". It is fixed in
  its own commit.
- **A hand-drawn box in the Generator could never be saved.** Only a proposal with results
  set `dirty`.

**The results worth carrying forward:**
- **The migration version gate struck a fourth time** (doc 22's bug). New `ADDED_COLUMNS`
  never reached a real install, because `run_migrations` returned early at
  `LATEST_VERSION`, and every test builds a fresh DB. The gate now also checks for missing
  added columns, so this cannot recur for columns. It still can for CHECK widening, which
  keeps needing the version bump.
- **React drops a queued updater for a component that unmounts in the same event.** The
  first cut of `usePersistentState` wrote to `localStorage` inside the updater. Start
  (remember the dataset, clear the name, unmount) lost the second write, and the next Start
  created a duplicate dataset. A single-setter test passes against the bug because of
  React's eager path; it takes two setters to reproduce it.
- **An autoplay loop must live outside React.** After every `await`, state is stale. A loop
  reading `session.save()` would write the previous image's boxes under the next image's
  path. The runner owns its position and passes reviews explicitly.

## Waiting on Jan — Wave 9

**A. See the demo-state yourself**, then say whether Wave 9 is done. PE4 flips it to
`complete` only on your word. The whole demo runs in `./scripts/dev.sh web`:
1. Generator → *A video file* → Play.
2. Stop during a hold, correct the frame, then Next.
3. Tick *Ask me when a score is between* and Play again.
4. *Inspect what I just annotated*, then click a bar and press ⇤ First.

**B. macOS privacy prompt.** A Python process started from the desktop app asked for
**~/Downloads** (the OSDaR23 data) and blocked the backend until it was answered. A
separate task is offered for moving that file IO off the event loop.

**C. Test data this build left behind**, for you to delete in Library if unwanted:
- Datasets: "Wave 9 action bar check" ×2, "Wave 9 dup check", "Wave 9 autoplay check" (50
  images) and "Wave 9 video check" (30 decoded frames).
- The test clip itself is in the session scratchpad, not the repo.

**D. Packaged-app checks.** Web mode is Chromium. Inspect paints through doc 68's
`FrameCanvas`, from `annotate/image` URLs that the packaged CSP already allows (doc 68's
`img-src` fix). That has not been seen in WebKit.

**E. Two tasks were offered out of scope:**
- Blocking file IO on the backend's event loop.
- Doc 68's claim of a `resolve_user_path` that does not exist.

---

## What landed after the Studio round — 2026-08-26/27

Most of it came from two sources. Jan used the app, and he made **a fresh clone on a second
machine**. That was the first time anyone set this project up anywhere except the machine
it was built on.

| | |
|---|---|
| 63 | **An API guide an AI assistant can follow.** The API already covered the whole workflow (51 paths). What was missing was the *order* things have to happen in. The guide is prose for the order and generated from `/openapi.json` for the endpoints, so it cannot go stale. "Copy for your AI" is the main button; PDF comes from `window.print()`. |
| 64 | **An MCP server at `/mcp`** on the sidecar that already runs. It exposes 15 tools shaped around tasks, and each tool dispatches into the app's own routes in-process. The "API" tab is now **Connection**, showing MCP first. |
| 65 | **A starter set** ("one click from clone to usable"). Five models, 1.1 GB, downloaded one after another from Admin. Grounded SAM is listed by name, with the parts it is built from. |
| 27↑ | **Grounded SAM in three sizes.** tiny+small 834 MB, base+base-plus 1,199 MB, base+large 1,747 MB. There is no larger open Grounding DINO. Provenance stays `grounded-sam` for all three. |
| 66 | **Grounding DINO everywhere.** `takes_concept` is its own field now instead of being read off `annotator_id`, and `PromptedDetector` is the fourth kind of foundation model. Also fixed: the Inference Viewer showed no models until a head was installed. |
| 67 | **Show masks, boxes or both**, with one `AnnotationView` toggle across three surfaces. The app now *says* what gets saved. Storage is not a choice: a mask exports with a bbox derived from it. |
| — | **Pretrained heads name their classes.** A bare `.pth` has no labels, so the ImageNet-1k and ADE20k label sets are vendored, declared per head type and resolved on read. `MaskLegend` finally uses `present_classes`, which had been on the wire since Wave 3. |
| 68 | **Video playback in the Inference Viewer.** Plays a folder or a video file (PyAV, about 35 MB). The chosen models run first as a job over a chosen frame range, with a cost estimate shown before the click, and the player reads from that cache. Frames are decoded linearly rather than seeked, so each overlay sits on exactly its own frame. There are two explicit modes: "A single image" and "A video or a folder". |
| fix | **Playback did not play, twice.** First, each frame was fetched only when the clock reached it, and the `<img>` src was swapped before the frame finished decoding. Frames are now prefetched 12 ahead, and folder frames go out as files. Second, frames are now painted to a canvas, because an `<img>` swapped on a clock is the engine's choice. **The packaged app's CSP `img-src` did not allow the sidecar**, so an installed build would have drawn nothing. `tauri dev` never applies that CSP. |
| fix | **Admin hid RF-DETR and Depth Anything.** `FAMILY_ORDER` was a hand-written subset that still typechecked. Order is now derived from the label record, and backend tests check the TypeScript union. |
| fix | **`dev.sh` on a clean clone.** It now checks for the Tauri CLI (`npm install --prefix apps/desktop`). If `rustc` prints no `host:` line, it prints rustc's own stderr instead of letting Tauri panic. |

**The ones to carry forward:**

- **`tauri dev` does not apply the packaged app's CSP.** Anything the page loads from the
  sidecar has to be in `tauri.conf.json`'s CSP, or it works in development and fails when
  installed. This belongs with the WebKit colour-management finding below: the dev loop and
  the shipped app are different engines under different rules.
- **Two lists that must agree should be one list.** `FAMILY_ORDER` failed this way, and so
  did the frontend's `ModelFamily` union, twice (`segmenter` in Wave 4, then `rf-detr`).
  Derive one from the other, or add a test that fails when they drift.
- **Don't let a probe change the product.** `crossOrigin` was added only so a verification
  probe could read the canvas back. It broke every prefetch with `ERR_FAILED`.

---

## What landed after Wave 8 — the Studio round, 2026-08-25

Reported by Jan from using the app, which is where all four of these came from and none of
them could have come from anywhere else.

| | |
|---|---|
| fix | **A drag on the image never drew a box.** The guard asked for `target === currentTarget`, and the image fills the stage, so it was the target of every press. Every unit test passed because they fire on the stage directly. |
| fix | **The Inference Viewer sent no concept.** `run` was memoised without `concept` in its deps, and the concept field only appears *after* a model is ticked — so the captured value was always `''`. Every SAM run returned an all-background mask in 26 ms. Compounded by the overlay painting class 0 opaque, which turned "no answer" into a full-frame colour wash. |
| 60 | **A class picker for boxes** — a `dataset_classes` table, GET/POST/DELETE, a dropdown with inline `New class…`, and per-class rename across an image. Closes doc 47's first known issue. |
| 61 | **Masks in the Studio** — Grounded SAM's segmentation is now shown and stored instead of discarded. One annotation per object: a mask row *or* a box row, never both, because the COCO exporter emits each table separately. |
| 62 | **Tiled inference** — the largest correctness gap, closed. A head trained on 472px tiles found nothing on a 2464px frame *while the run succeeded*. Per-run grid, merged with class-aware NMS. Measured 0 boxes against 6 on the frame the gap was found in. |
| — | **Segmentation heads train** — `linear-segmenter` was registered trainable with a loss wired to it and nothing that could produce its target. Class 0 is background; `unclear` paints over positives; an unsegmented image is not an empty one. |
| — | **Training tab, and a model guide in the intro** — 'Head Trainer' did two things and named one, so fine-tuning was never found. The intro now says which model is for what, with numbers measured here. |

**The one to carry forward: WebKit colour-manages canvas image data whatever you ask.**
`createImageBitmap(blob, { colorSpaceConversion: 'none' })` does not stop it — proved by
giving the two mask surfaces different defences and seeing exactly one survive. Anything
transported as a PNG whose pixels are *data* must assume the low bits are unreliable in the
packaged app. Two defences that work: threshold rather than `> 0` (binary masks), and spread
class indices across the byte and send the multiplier (`encode_class_map` / `class_stride`).

**Chromium cannot reproduce any of it.** A dev-browser check is not evidence for a rendering
fix; the packaged app is.

---

## Waiting on Jan

**0. Confirm the Dataset Generator's masks are clean in the packaged app.** The Studio and
the Inference Viewer were both confirmed fixed on 2026-08-25 — the Viewer by the
`class_stride` change, after `colorSpaceConversion: 'none'` turned out not to be honoured.
The Generator was the third surface to show the same speckle, because each had grown its own
compositor; they share one now (`CompositedMasks`), so this should be the last of it.

**0b. Confirm video playback in the packaged app** (doc 68). It was verified in `tauri dev`
and the dev browser. Neither applies the CSP that the `img-src` fix changed, so a built
`.app` is the only real evidence that frames draw.

**0c. Connect a real MCP client once** (doc 64). Every test drives the JSON-RPC endpoint
directly. The `claude mcp add` command in the Connection tab has been written but never
executed. Also still open: whether PyInstaller picks up `mcp` in the frozen sidecar.

**1. Certificates — the one thing that cannot be done here.** Signing needs an Apple
Developer ID and a Windows code-signing certificate. Until they exist:

- the macOS build is **Gatekeeper-blocked on first launch**,
- the Windows build shows a **SmartScreen warning**,
- `release.yml` publishes a **draft** rather than a live release, deliberately, so an
  unsigned build cannot reach anyone by accident. **Keep that guard until signing lands.**

**2. Nobody has ever installed this app.** The macOS `.app` was launched from its own build
directory, on the machine that built it, and shared that machine's model cache and data
directory. Windows and Linux **build** and have never been run at all. *(On 2026-08-26 a
fresh **clone** on a second machine did happen, and it paid off at once: docs 65 and the
`dev.sh` fixes came out of it. But that was the developer path, not an installer.)* Installing each
artefact on a clean machine is the highest-value hour available right now, and it needs
machines rather than code.

**3. The `Open folder` button has never been clicked.** It is Tauri-only and this session
cannot drive a native webview (doc 59). Everything around it is verified; the OS call is
not.

**4. `THIRD_PARTY_LICENCES.txt` is a judgement call worth a second opinion.** torch's
vendored licence texts are flattened into one file to get under Windows' MAX_PATH (doc 58).
The texts are unmodified and each carries its original path, which should satisfy BSD/MIT
attribution — but that is a legal reading, not a technical one.

---

## What Wave 8 turned out to be

Six docs, 54–59. Two of them the wave never asked for.

| | |
|---|---|
| 54 | What shipping obliges — three licence obligations, not one |
| 55 | Unfreezing — where it works, and where it cannot |
| 56 | Freezing the sidecar — the spike that constrained everything |
| 57 | GPU support as a download |
| 58 | A real installer, then CI written from what worked |
| 59 | Open a dataset's folder |

**Deferred to the backlog**, each with its reasoning there: code signing, auto-update, and
a first-run experience on a clean machine.

## The four results worth carrying forward

**1. A head cannot carry a backbone, and that is what "head" means here.** Training one
scored **0.000 mAP** in a fresh process — a `HeadInstance` stores head weights beside a
`backbone_id`, so a modified backbone is discarded, and the run reports a plausible
validation number the whole way. Unfreezing lives on the **fine-tune** path, which saves
the whole model: measured there at mAP 0.781 → **0.843** for 19% more time, because that
path never had a feature cache to give up. This is also the real answer to "why isn't
RF-DETR a head".

**2. The runtime is the size problem, not the weights.** The frozen sidecar is 636 MB
before a single model is downloaded. Installers land at **181 MB (Windows, NSIS)**, 311 MB
(macOS, dmg), 377 MB (Linux, deb) — and Windows being *smallest* is the opposite of the
intuition; NSIS's LZMA squeezes torch hardest.

**3. A CUDA torch wheel is 2532 MB on Windows against 111 MB for CPU.** That single number
decided the packaging strategy: ship CPU, offer GPU as a download (doc 57). `--index-url
.../whl/cpu` in `release.yml` is load-bearing — without it every Windows and Linux
installer is over 2.5 GB.

**4. AppImage cannot package this payload.** Isolated across CI runs 2 and 3: `appimage,deb`
fails, `deb` alone passes. AppImage repacks the whole tree through `linuxdeploy` and the
tree is 636 MB of PyInstaller `_internal`. **Linux ships `.deb` only**, which excludes
distributions that do not take one.

---

## Known gaps, in the order they will bite

1. ~~**No tiled inference.**~~ **Fixed 2026-08-25 (doc 62.)** Measured on the frame it was
   found in: 0 boxes whole-frame against 6 tiled, at a threshold where the whole-frame run
   finds nothing at any setting. Per-run grid, with a hint when a head's training width is
   far below the frame's. What it still does not cover is in doc 62's Known Issues —
   foundation proposals, masks and depth.
2. **No signing** (backlog) — blocks any real distribution.
3. **The GPU sidecar has no artefact** (doc 57). Detection works and tells the user their
   GPU is idle; there is nothing to download yet, because that is a second CI matrix leg.
4. **A random split leaks on video** (doc 49, backlog). `split_indices` splits by image,
   which is right for photos and wrong for a 10 Hz sequence. It inflated a reported mAP by
   42%, and nothing warns. **More urgent since doc 68** made video a first-class input,
   which makes the gap easier to walk into. Segment-aware splitting needs its own doc.
5. **Prescan shares one runner** across the Studio and the Generator (doc 53).
6. **Renaming is missing from the Library** (doc 51). *(Per-class rename from box review
   was the other half of this line and shipped in doc 60 on 2026-08-25.)*
7. ~~**`linear-segmenter` is declared trainable but cannot run.**~~ **Fixed 2026-08-25** —
   it trains on stored masks now; see the backlog entry for the decisions and the one thing
   only a real run caught. The vocabulary is per task rather than unioned, so a segmenter
   never sees a box-only class — which was worth more than it sounded: dropping one dead
   channel took epoch-1 loss from 3.16 to 0.70 and best mIoU from 0.263 to 0.539.
8. **The MCP server and the API guide are local only, with no auth** (docs 63, 64). That is
   fine on one machine. Remote access needs authentication and path confinement first; see the
   hosted-GUI entry in the backlog. Jobs are poll-only, with no MCP progress notifications.
9. **`window.print()` for the guide's PDF is unverified in WKWebView** (doc 63). The
   Markdown path, which is the one that matters for an assistant, does not depend on it.

---

## If you are picking this up cold

Read `.mdd/.startup.md` for the map, then `.mdd/waves/dinotraining-wave-8.md`, then docs
**56** and **58** (what packaging actually costs), **55** (why a head is a head), and **49**
(the hardest data problem in the project). For the newest surface, video, read **68**,
including its "Why playback did not play" section.

**MDD hashes** must be recomputed after any initiative/wave edit:

```bash
f=.mdd/waves/dinotraining-wave-8.md
new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
perl -pi -e "s/^hash: .*/hash: $new/" "$f"
```

**Gates**, all green on `feat/dinotraining-wave-9` as of 2026-09-29: `1471` backend tests,
`970` frontend, `ruff` + `mypy` + `tsc` clean. Files over 300 lines predate Wave 9
(`app/ml/registry.py`, `app/ml/heads/registry.py`, four test files). `cargo check` was not
run: nothing in Wave 9 touched `apps/desktop`.

**Worktree note:** this session worked in a git worktree with `node_modules`, `backend/.venv`
and `.env` **symlinked** from the main checkout (all gitignored, all excluded from git
status). A fresh worktree needs the same, or `npm ci --legacy-peer-deps` plus a venv.

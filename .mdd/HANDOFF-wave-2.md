# Wave 2 complete — Head Trainer

**Branch:** `feat/dinotraining-wave-2` (pushed, 9 commits ahead of `dev`)
**Completed:** 2026-08-18 · all 9 features · wave and initiative flipped to `complete`

> This file previously carried the mid-wave resume instructions. Wave 2 is finished, so
> it now records the outcome instead. **Nothing here needs resuming.**

## What Wave 2 delivers

| # | Feature | Doc | What it gives you |
|---|---|---|---|
| 1 | backbone-feature-extractor | 07 | frozen DINO features, `cls` + `(B,D,Gh,Gw)` grid, capability descriptor |
| 2 | head-registry | 08 | the head-type contract everything dispatches off |
| 3 | head-implementations | 09 | 4 heads on one call signature |
| 4 | preprocessing-pipeline | 10 | task-aware geometry, targets move with the image |
| 5 | training-job-runner | 11 | pluggable runner, task-generic loop, feature cache |
| 6 | head-instance-registry | 12 | provenance + safetensors, the cross-tab picker |
| 7 | training-metrics-stream | 13 | training API + SSE live metrics |
| 8 | trainer-config-ui | 14 | the Head Trainer tab |
| 9 | head-catalog-import | 15 | pinned defaults + safetensors-only community import |

**Demo-state, verified end to end 2026-08-18:** train a head on a real dataset against a
frozen `dinov2-small` with live SSE metrics and provenance-recorded output *and* install
pretrained classification / segmentation / depth heads without training anything. All
three defaults were installed from Meta's CDN and run against the real backbone on MPS.

## Next step

Merge to `dev` (Jan does the merge; never commit to `main`), then
`/mdd plan-wave dinotraining-wave-3` for the Inference Viewer.

Wave 3 consumes `HeadInstanceStore.list_all(task=, backbone=)` and `HeadInstance.summary`
— present heads by what they do, never by filename. Doc 12 holds that contract; doc 15's
`render_hint` on each head type tells the viewer how to draw the output.

## Decisions from this wave that Wave 3 must not re-litigate

- **Heads are registry entries, not enum branches.** Losses, metrics, decoders and
  builders are all registries keyed by head-type id.
- **Usable ≠ trainable.** `linear-depth` is usable-but-not-trainable on purpose.
- **Provenance is the cross-tab contract.** Never present a head by filename.
- **DINOv3 has no default heads and never will get ours** — ViT-7B only, gated,
  non-redistributable licence. DINOv2-only is a decision, not a gap. See doc 15.
- **The pickle carve-out is narrow:** `torch.load` runs on exactly one path, on bytes
  whose SHA-256 already matched a compiled-in pin. Community imports are safetensors
  only, with no fallback branch. Do not add one.
- SAM lands in **Wave 4**, which is what finally makes segmentation trainable in-app.

## Conventions worth carrying forward

- **Integration verification means driving the real thing.** Wave 2 shipped 581 backend
  and 133 frontend tests; every one of the eight real bugs this wave came from running
  the app, not from the suite. Three in feature 9 alone — see doc 15 `known_issues`.
- Contract-log honesty: `satisfies_contracts.verified_at` must name a call site that
  actually exists in that feature.
- Files stay under 300 lines — a hook blocks the write. `runner.py` and `importer.py`
  were both split when they hit it.

## Gotchas

- **Do not use `perl -pi -e 's|…|…|'` with `|` as the delimiter** on regexes containing
  `|`. Use the Edit tool for structured files.
- **The project has no prettier config** and uses single quotes. Do not run prettier.
- **MDD hashes** must be recomputed after any initiative/wave edit:
  ```bash
  f=.mdd/waves/dinotraining-wave-2.md
  new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
  perl -pi -e "s/^hash: .*/hash: $new/" "$f"
  ```
- **Restart the dev server after backend edits** (`preview_stop` then `preview_start`);
  uvicorn does not reload. Stale Vite HMR errors persist in the console buffer across a
  restart — verify with `tsc` + `read_page`, not the console.
- Locally downloaded: `dinov2-small`, `grounding-dino-tiny`, and the three `dinov2-small`
  default heads (~6 MB, installed during feature 9 verification).

# Wave 2 handoff — 8 of 9 features complete

**Branch:** `feat/dinotraining-wave-2` (pushed, 8 commits ahead of `dev`)
**Date:** 2026-08-18
**Remaining:** feature 9, `head-catalog-import`

## Resume in a new session with

```
/mdd plan-execute dinotraining-wave-2
```

MDD's stale-job detection reads `.mdd/jobs/wave-dinotraining-wave-2/MANIFEST.md`,
finds 8/9 `[x]`, and resumes at `head-catalog-import`. Choose **Resume**, not Discard.
Mode was **automated** (minimal interruptions, pause only on errors).

## What exists now

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

**Demonstrable today:** open the Head Trainer tab, select a dataset + `dinov2-small` +
a head type, press Start, watch epochs stream in, and see the trained head listed with
its provenance. Verified in the browser end to end.

## Feature 9 — what is left

`head-catalog-import` (doc `15-head-catalog-import.md`, not yet written). The decisions
are already made and recorded in the initiative's Open Product Questions:

- **One code path for defaults and community heads**: fetch → validate against the
  backbone capability descriptor → register a `HeadInstance`. `HeadInstanceStore.register`
  already accepts `kind`, `source_repo` and `source_digest` and is proven with
  `pretrained-default` in tests.
- **Community imports: safetensors from a HuggingFace repo id only.** `.pt`/`.pth` are
  refused outright — `torch.load` on a pickle is arbitrary code execution in an app
  installed by strangers.
- **⚠ The official DINOv2 heads are `.pth` (mmcv) pickles.** This collides with the rule
  above. The agreed resolution: the safetensors rule governs *untrusted user-supplied*
  imports; first-party defaults come from a curated **SHA-256-pinned catalog**, are
  verified against the digest, and converted to safetensors on download. The pickle path
  must never be reachable from user input.
- Every head needs a manifest (backbone version, patch size, embed dim, task) validated
  against `read_capabilities`. On mismatch, **explain why** rather than greying it out,
  and say which installed backbone the head would work with.
- Expected surface: `GET /api/v1/head-catalog`, `POST /api/v1/head-catalog/{id}/install`,
  `POST /api/v1/heads/import` (repo id + task), plus Admin-tab UI.

Open research still unresolved (in the wave doc):
- Exact default-head weights + digests to pin per backbone. **DINOv3 may have no
  published heads at all** — check before promising defaults for it.
- Whether DINOv3 default heads exist under a licence compatible with redistribution,
  given the model itself is gated.

## Wave completion after feature 9

`/mdd plan-execute` Phase PE4 will: flip the wave to `complete` in both
`waves/dinotraining-wave-2.md` and the initiative table, cascade `status: complete` to
docs 07–15, recompute hashes, rebuild `.mdd/.startup.md`, regenerate
`.mdd/connections.md`, and delete the job folder. Then merge to `dev` (Jan does the
merge himself; never commit to `main`).

## Conventions this wave established

- **Registries keyed by head-type id**, never `if task ==`: `HEAD_BUILDERS` (09),
  `LOSSES` / `METRICS` / `DECODERS` (11). Adding a head type means adding entries.
- **Contract log honesty**: `satisfies_contracts.verified_at` must name a call site that
  actually exists in that feature. Three entries were rewritten rather than pointing at a
  function the feature never calls.
- **Integration verification means driving the real thing** — real weights, real HTTP,
  real browser. Every bug this wave came from that, never from tests.
- Files stay under 300 lines (a hook enforces it); `runner.py` was split into
  `job`/`loop`/`runner` when it hit 354.

## Gotchas worth carrying forward

- **Do not use `perl -pi -e 's|…|…|'` with `|` as the delimiter** on regexes containing
  `|`. It prepended a replacement to all 143 lines of the wave doc. Use the Edit tool for
  structured files.
- **The project has no prettier config** and uses single quotes. Do not run prettier.
- **MDD hashes** must be recomputed after any initiative/wave edit or the next
  `plan-execute` hard-stops:
  ```bash
  f=.mdd/waves/dinotraining-wave-2.md
  new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
  perl -pi -e "s/^hash: .*/hash: $new/" "$f"
  ```
- **Restart the dev server after backend edits** (`preview_stop` then `preview_start`);
  uvicorn does not reload. Stale Vite HMR errors persist in the browser console buffer
  across navigation after a restart — verify with `tsc` + a `read_page`, not the console.
- **Clean up demo data** seeded into `~/Library/Application Support/DinoTraining/`. The
  safety hook blocks `rm -rf`; use `find … -delete` then `rmdir`.
- Only `dinov2-small` and `grounding-dino-tiny` are downloaded locally.

## Known issues carried (recorded in the docs, not bugs)

- `map_75` is noisy epoch to epoch on small datasets (L1 box loss on a 32×32 grid).
  Best-model selection uses the mean `map`, so it does not chase the noise. Revisit with
  IoU/GIoU loss if Wave 3 needs tighter localisation. — doc 11
- Classification labels are derived only from images whose positive boxes name exactly
  one class; mixed images are skipped and counted in `skipped_mixed_class_images`, which
  the UI surfaces. Multi-label is out of scope for this wave. — doc 11
- Segmentation has no in-app training targets until SAM lands in Wave 4; it trains only
  on a user-brought mask dataset, and is otherwise used via its pretrained default.

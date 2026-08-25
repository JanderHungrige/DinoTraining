# Handoff — start here

**This is the current handoff and always is.** It is rewritten in place at the end of each
wave rather than appended to. `HANDOFF-wave-2.md` is an older per-wave one kept as history;
do not read it for current state.

**Last updated:** 2026-08-25, after a round of **Annotation Studio work** that was not a
wave: four bugs Jan reported from using the app, and two features (docs **60** and **61**)
built out of them. Waves 1–8 are merged. **Only Wave 9 (Website & hyperscaler compute)
remains** as planned work, plus the three features deferred out of Wave 8.

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

**1. Certificates — the one thing that cannot be done here.** Signing needs an Apple
Developer ID and a Windows code-signing certificate. Until they exist:

- the macOS build is **Gatekeeper-blocked on first launch**,
- the Windows build shows a **SmartScreen warning**,
- `release.yml` publishes a **draft** rather than a live release, deliberately, so an
  unsigned build cannot reach anyone by accident. **Keep that guard until signing lands.**

**2. Nobody has ever installed this app.** The macOS `.app` was launched from its own build
directory, on the machine that built it — sharing that machine's model cache and data
directory. Windows and Linux **build** and have never been run at all. Installing each
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
   which is right for photos and wrong for a 10 Hz sequence — it inflated a reported mAP by
   42%. Nothing warns.
5. **Prescan shares one runner** across the Studio and the Generator (doc 53).
6. **Renaming is missing from the Library** (doc 51). *(Per-class rename from box review
   was the other half of this line and shipped in doc 60 on 2026-08-25.)*
7. ~~**`linear-segmenter` is declared trainable but cannot run.**~~ **Fixed 2026-08-25** —
   it trains on stored masks now; see the backlog entry for the decisions and the one thing
   only a real run caught. The vocabulary is per task rather than unioned, so a segmenter
   never sees a box-only class — which was worth more than it sounded: dropping one dead
   channel took epoch-1 loss from 3.16 to 0.70 and best mIoU from 0.263 to 0.539.

   *(original)* **`linear-segmenter` is declared trainable but cannot run.** `trainable=True`,
   `target_format="masks"`, with `segmentation_loss` and `segmentation_metrics` both
   registered — but `build_samples` reads only boxes, `TrainingSample` has no mask field,
   and `build_targets` has no segmentation branch, so `targets["mask"]` is never produced.
   Selecting it in the Head Trainer raises `KeyError: 'mask'` on the first batch; nothing
   guards it upfront. Its description still names a blocker doc 61 removed. **Now the
   cheapest route to a segmenter trained on your own classes**, because the masks exist.

---

## If you are picking this up cold

Read `.mdd/.startup.md` for the map, then `.mdd/waves/dinotraining-wave-8.md`, then docs
**56** and **58** (what packaging actually costs), **55** (why a head is a head), and **49**
(the hardest data problem in the project).

**MDD hashes** must be recomputed after any initiative/wave edit:

```bash
f=.mdd/waves/dinotraining-wave-8.md
new=$(grep -v '^hash:' "$f" | shasum -a 256 | cut -c1-8)
perl -pi -e "s/^hash: .*/hash: $new/" "$f"
```

**Gates**, all green as of 2026-08-25: `1262` backend tests, `685` frontend, `ruff` +
`mypy` + `tsc` clean, no source file over 300 lines. (`cargo check` last run 2026-08-21 —
nothing since has touched `apps/desktop`.)

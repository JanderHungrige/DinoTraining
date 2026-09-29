# Handoff — start here

**This is the current handoff and always is.** It is rewritten in place at the end of each
wave rather than appended to. `HANDOFF-wave-2.md` is an older per-wave one kept as history;
do not read it for current state.

**Last updated:** 2026-09-29. It catches up on two rounds of work that were not waves:
the **Studio round** (2026-08-25, docs 60–62) and the **agent, first-run and video round**
(2026-08-26/27, docs 63–68). Everything below is merged to `dev` and `main`, and `main`
is at `d47ed26`. Nothing has been pushed since 2026-08-27. Waves 1–8 are merged.
**Wave 9 (Generator Autopilot & Dataset Inspection) was inserted on 2026-09-29 and is
in progress on `feat/dinotraining-wave-9`**; the website wave is now **Wave 10**. Plus the three
features deferred out of Wave 8.

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

**Gates**, as last reported by the commit that closed doc 68 (2026-08-27): `1431` backend
tests, `842` frontend, and no source file over 300 lines. They were not re-run when this
handoff was rewritten on 2026-09-29. `apps/desktop` **has** changed since the last
`cargo check` (2026-08-21): the CSP in `tauri.conf.json` changed on 2026-08-27. That is config,
not Rust, but `cargo check` / a packaged build is the next check worth running.

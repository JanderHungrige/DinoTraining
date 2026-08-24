# Handoff — start here

**This is the current handoff and always is.** It is rewritten in place at the end of each
wave rather than appended to. `HANDOFF-wave-2.md` is an older per-wave one kept as history;
do not read it for current state.

**Last updated:** 2026-08-21, after **Wave 8** was closed. Waves 1–8 are merged to `dev`
and `main`. **Only Wave 9 (Website & hyperscaler compute) remains**, plus three features
deferred out of Wave 8.

---

## Waiting on Jan

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

1. **No tiled inference** (doc 49, backlog). A head trained on 472 px tiles finds nothing on
   a full frame and says nothing about why. Still the largest correctness gap.
2. **No signing** (backlog) — blocks any real distribution.
3. **The GPU sidecar has no artefact** (doc 57). Detection works and tells the user their
   GPU is idle; there is nothing to download yet, because that is a second CI matrix leg.
4. **A random split leaks on video** (doc 49, backlog). `split_indices` splits by image,
   which is right for photos and wrong for a 10 Hz sequence — it inflated a reported mAP by
   42%. Nothing warns.
5. **Prescan shares one runner** across the Studio and the Generator (doc 53).
6. **Renaming is missing from the Library** (doc 51), and **per-class rename** from box
   review (doc 47).

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

**Gates**, all green as of 2026-08-21: `1185` backend tests, `565` frontend, `ruff` +
`mypy` + `tsc` + `cargo check` clean, no source file over 300 lines.

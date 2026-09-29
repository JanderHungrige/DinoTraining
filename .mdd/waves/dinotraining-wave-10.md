---
id: dinotraining-wave-10
title: "Wave 10: Look & Feel — Living Background, Hand-Drawn Controls, Lato"
initiative: dinotraining
initiative_version: 10
status: in_progress
depends_on: dinotraining-wave-9
demo_state: "The app opens over a seamlessly looping particle background with no visible jump at the loop point. Every button has NinaNatur's hand-drawn outline, all text is set in Lato, and every screen stays legible, and calm under reduced motion, in the packaged app and not only the dev browser."
created: 2026-09-29
hash: f572ad9b
---

# Wave 10: Look & Feel

Requested by Jan on 2026-09-29:
- Download the Pixabay video *Octagon Abstract Lights Particle* (#5192) and mirror-stitch it,
  so it loops seamlessly, for use as the app's background.
- Give buttons the outline look from the NinaNatur project.
- Use Lato as the font.

Planned with Jan's choices:
- **Draft Sketch** is the NinaNatur look meant: `frontend/src/themes/draft-sketch/ours/controls.css`
  in `~/Code/NinaNatur`.
- This wave comes first of the three new ones, ahead of Preprocessing (11) and Fine-tuning
  (12). The website moved 10 → 13.

## Demo-State

1. **Seamless loop.** Launch the packaged app: the particle video plays behind every tab,
   and the loop point cannot be seen, because the clip plays forwards and then mirrored
   backwards.
2. **Draft Sketch buttons.** Every button has the hand-drawn outline, and the style reads on
   the dark video: light ink, a translucent wash, the offset shadow, a slight turn on hover
   and a press on click.
3. **Lato everywhere, offline.** All text is Lato, loaded from the app itself.
4. **Reduced motion.** With the OS setting on, the background is a still frame and the
   buttons do not move.
5. **Legibility.** Every panel still meets WCAG AA contrast over the brightest frame of the
   video.

*(Not complete until this can be manually demonstrated, in the packaged app.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | background-video-asset | docs/76-background-video-asset.md | complete | — |
| 2 | app-background-layer | — | planned | background-video-asset |
| 3 | lato-typography | — | planned | — |
| 4 | draft-sketch-controls | — | planned | lato-typography |
| 5 | legibility-and-motion-pass | — | planned | app-background-layer, draft-sketch-controls |

### Feature notes

1. **background-video-asset.**
   - **Download:** Download the source from Pixabay: https://pixabay.com/videos/octagon-abstract-lights-particle-5192/.
     This needs Jan's go-ahead at build time, stating the file name, source and size.
     If Pixabay puts a login or a CAPTCHA in front of the download, Jan downloads it himself
     and hands over the path. Claude does not get past bot checks.
   - **Mirror-stitch** with PyAV, which is already a backend dependency (doc 68):
     frames 0…N, then N−1…1, so the last frame leads straight back into the first.
     Encode as H.264 MP4, which WKWebView plays natively.
   - **Size is a budget, not a detail.** The installer is 181–377 MB (doc 58), and the
     background should add single-digit MB. Downscale to ≤ 1280 px, use a low bitrate, and
     measure it. A poster JPEG (a still frame) is produced for reduced motion and for the
     first paint.
   - **Licence:** the Pixabay Content License allows use inside an app without attribution,
     but not redistribution of the file on its own. Record it in doc 54's obligations and in
     `THIRD_PARTY_LICENCES`. The asset is committed with its provenance, as media rather than
     weights. CLAUDE.md's "never commit" list is weights, checkpoints and datasets.
2. **app-background-layer.**
   - A fixed `<video muted autoplay loop playsinline>` sits behind the tab panels, which
     become translucent surfaces with a blur where WebKit supports it.
   - Under `prefers-reduced-motion`, the poster is shown instead.
   - The video pauses when the window is hidden (`visibilitychange`), so it costs no GPU in
     the background.
   - An "Animated background" switch in Admin, remembered via doc 69, turns it off.
   - **The CSP needs `media-src 'self'`**, and `tauri dev` does not apply the packaged CSP.
     This is doc 68's lesson, and it is why the demo is in the packaged app.
3. **lato-typography.**
   - Lato 400/700 (+ italic 400) is **self-hosted** as woff2 (`@fontsource/lato`, or the
     Google Fonts files), not loaded from the Google CDN. The desktop app must work offline,
     and a CDN is a request to Google on every launch.
   - Lato is SIL OFL 1.1, which goes into doc 54's licence list.
   - `font-display: swap` avoids a blank first paint.
4. **draft-sketch-controls.** A port of NinaNatur's Draft Sketch controls, with its provenance
   noted as NinaNatur does it:
   - the asymmetric edge (`255px 14px 225px 16px / 16px 225px 14px 255px`), a 1.5 px line
     and a 1px/2px offset shadow;
   - hover turns −0.6° with a deeper wash, active presses 1px/2px, and `aria-pressed` is
     drawn heavier.
   - **Adapted to a dark, moving background:** light ink instead of `#1c2419`, a translucent
     wash in the app's accent, and Lato instead of Patrick Hand.
   - Applies to `.btn`, the toggles, `genbar__auto`, the timeline rows and tabs.
   - **Focus rings are never removed.** Reduced motion drops the turn and the press.
   - Two open questions for the build: primary buttons keep the filled wash; disabled
     buttons fade the ink rather than the wash.
5. **legibility-and-motion-pass.**
   - **Contrast:** measure contrast over the brightest frame of the loop, for text, dim text,
     the overlay labels in the canvases and the timeline bars.
   - **Canvas views:** check the Inspect player and the mask canvases. They must not show
     the video through the image area.
   - **Screenshots:** take them in the packaged app, in light and dark OS appearance, and
     with reduced motion on.

## Open Research

- **Whether Pixabay's download is scriptable**, or needs Jan in the loop (login or CAPTCHA).
- **What a full-screen video costs on this machine** alongside the heavy views: mask
  compositing, the Inspect player and SAM runs. Measure CPU and GPU with it on and off,
  and decide whether it pauses while a model runs.
- **Blur support:** does WKWebView's `backdrop-filter` blur hold up over a playing video,
  or is a solid translucent surface the reliable choice?

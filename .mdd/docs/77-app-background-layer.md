---
id: 77-app-background-layer
title: App Background Layer — The Loop Behind Every Tab
edition: DinoTraining
depends_on: [76-background-video-asset, 69-remembered-entries]
relates: [01-app-shell, 80-legibility-and-motion-pass]
source_files:
  - apps/frontend/src/components/BackgroundVideo.tsx
  - apps/frontend/src/hooks/useReducedMotion.ts
  - apps/frontend/src/lib/look.tsx
  - apps/frontend/src/App.tsx
  - apps/frontend/src/components/AppearancePanel.tsx
  - apps/frontend/src/tabs/AdminTab.tsx
  - apps/frontend/src/styles.css
  - apps/frontend/src/look.css
  - apps/desktop/src-tauri/tauri.conf.json
routes: []
models: []
test_files:
  - apps/frontend/src/components/BackgroundVideo.test.tsx
  - apps/frontend/src/components/AppearancePanel.test.tsx
data_flow: greenfield
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [look-and-feel, video, accessibility, reduced-motion, csp, app-shell]
path: App Shell/Look & Feel
initiative: dinotraining
wave: dinotraining-wave-10
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "Browser-pane screenshots do not capture a playing <video> (the frame is composited as an overlay), so visual proof here is the poster fallback plus currentTime advancing. The packaged-app demo is where the moving loop gets seen."
  - "The surfaces are tuned by eye: panel 52 %, header and tabs 70 %, scrim 0.5→0.38, with the content cards staying solid. Doc 80 measures contrast over the brightest frame and may raise them." 
security_read_sites: []
sister_projects: []
---

# 77 — App Background Layer

## Purpose

This puts doc 76's loop behind the whole app, so it plays behind every tab, without costing
legibility, battery or accessibility.

## Architecture

```
<LookProvider>            animated-background preference, remembered (doc 69), shared
  <BackgroundVideo/>      fixed, full-window, aria-hidden, behind everything
     ├ video  muted autoplay loop playsInline, poster = particles-poster.jpg
     ├ reduced motion or switched off → the poster <img> only
     └ scrim   a dark (light-mode: pale) veil; the video is atmosphere, never contrast
  <div class="app">       header, tab bar and panel become translucent, blurred surfaces
Admin › Appearance        [☑ Animated background]
```

## Business Rules

1. **Decorative, and announced as nothing.** `aria-hidden`, no controls, not focusable,
   `pointer-events: none`.
2. **`prefers-reduced-motion: reduce` shows the still poster**, and so does the switch in
   Admin being off. It is checked live: changing the OS setting takes effect at once.
3. **Hidden window, paused video.** On `visibilitychange` the video pauses, and resumes
   when visible, so a minimised app decodes nothing.
4. **A scrim is always on.** The video is warm and bright (doc 76), and text contrast is
   carried by the surfaces and the scrim, never by hoping the frame is dark. Doc 80 measures
   it.
5. **Canvases stay opaque.** The annotation canvases, the Inspect player stage and the
   viewer letterbox keep their solid backgrounds: annotation work must never show particles
   through an image.
6. **The CSP names it:** `media-src 'self'`. `default-src 'self'` would already allow it,
   but this app has been caught by CSP differences between `tauri dev` and the packaged
   build (doc 68), so the rule is spelled out rather than inherited.
7. **The preference is shared, not duplicated.** Admin's switch and the layer read one
   context. Two `usePersistentState` calls on one key would not see each other's writes.

## Verified in the running app (2026-09-29)

- **The first pass hid the video completely.** Panels at 84 % and a scrim at 72 % made the
  app look unchanged. They were lowered to 52 % and 70 %, with the scrim at 0.5→0.38 and
  the content cards still solid.
- **With the Admin switch off, the poster shows**: warm, blurred bokeh behind the header
  and the panel edges, while the cards stay solid and legible (screenshot). The same switch
  turned it back on.
- **The video is playing.** `currentTime` went 1.48 → 3.49 s over 2 s, and seeking to 57.5 s
  wrapped to 0.7 s, so the loop restarts without stopping. The preference was stored as
  `true`.
- **A start blocked in a background window is retried on mount.** Before that fix, the pane
  opened hidden, the start was blocked, and only a later visibility change would have
  started it.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

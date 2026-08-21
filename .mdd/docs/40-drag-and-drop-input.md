---
id: 40-drag-and-drop-input
title: Drag-and-Drop Input — Desktop Only, Because Only There Is There a Path
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7
wave_status: complete
depends_on: [17-image-input-source, 06-annotation-workflow]
relates: [26-generator-review-ui, 19-side-by-side-viewer, 39-prompt-guidance]
source_files:
  - apps/frontend/src/lib/dragDrop.ts
  - apps/frontend/src/hooks/useFileDrop.ts
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/components/ImageSourcePicker.tsx
  - apps/frontend/src/styles.css
routes: []
models: []
test_files:
  - apps/frontend/src/lib/dragDrop.test.ts
data_flow: reads-existing
last_synced: 2026-08-20
status: complete
phase: all
mdd_version: 11
tags: [drag-and-drop, tauri, input-source, desktop, annotation-studio, inference-viewer]
path: Annotation Studio/Input
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**Not verified against a running desktop app.** The browser branch was verified (no affordance offered, nothing else affected) and the types check against the real `@tauri-apps/api` 2.11.1 `DragDropEvent`. The drop itself needs a human to drag a folder onto the Tauri window, which no automated check here can perform. Treat the desktop path as written-and-typed, not exercised — this is the one thing in Wave 7 that wants a manual look."
  - "The drop is **window-level**, not per-field: Tauri reports a drop on the webview, not on what was under the cursor. Harmless while one tab is mounted at a time — exactly one listener exists — but a future split view with two path fields would need targeting the current event does not provide."
  - "Only the first dropped path is used. Dropping twelve images means one folder; dropping two *different* folders silently takes one. Refusing would be defensible; picking the first matches what the field can hold."
  - "`folderOf` decides file-vs-folder by extension, because the frontend has no `stat` and a round trip would make a drop feel slow. A directory named `photos.png` is mishandled."
sister_projects: []
---

# 40 — Drag-and-Drop Input

## Purpose

Let images be added by dragging them onto the window, instead of only by typing a path or
opening the native picker.

## Architecture

**Desktop only, decided before building** — the wave doc called this out as the question to
settle first. Measured against the installed `@tauri-apps/api` 2.11.1:

| | Tauri | Browser |
|---|---|---|
| drop yields | `{type: 'drop', paths: string[]}` | `File` objects |
| filesystem path | **yes** | **no** |
| feeds doc 17 | directly | not at all |

A browser drop has nothing the backend can open. The alternative was an upload endpoint —
a second input contract, the one doc 17 deliberately avoided, plus a temp-file lifecycle to
own. Instead the affordance is **not offered** where it cannot work, which is the pattern
`hasNativeDialog` already set: the browse buttons disappear, the path field never does. If
browser input is ever wanted it belongs in Wave 9, where server-side files are already part
of the deal.

```
Tauri webview ──▶ onDragDropEvent ──▶ useFileDrop ──┬─▶ Studio     folderOf(path)
   enter/leave ──▶ hover affordance                 ├─▶ Generator  folderOf(path)
                                                    └─▶ Viewer     path as-is
```

## Business Rules

1. **A dropped image means its folder** — in the Studio and the Generator, which take a
   folder. People drop the images they can see, and being told "not a folder" is a worse
   answer than doing the obvious thing. `folderOf` decides by extension: the frontend has
   no `stat`, and asking the backend would make a drop feel slow.
2. **The Inference Viewer takes the path as-is.** Doc 17's source contract accepts a single
   image *or* a folder and returns the same shape either way, so a dropped file is already
   valid input and `folderOf` would throw information away.
3. **Hovering is acknowledged.** `enter`/`leave` drive a dashed outline and a changed
   label — accepting a drop with no visible response reads as nothing having happened.
4. **The affordance is hidden, never disabled, where drops are unavailable.** A greyed-out
   drop zone in a browser explains nothing; its absence, next to a working path field,
   explains itself.
5. **Subscribing outside Tauri is a no-op, not an error.** Callers wire it up
   unconditionally — making each one check first is how one of them eventually forgets.

## Data Flow

`paths[0]` → `folderOf` (Studio, Generator) or unchanged (Viewer) → the same state the text
field writes. Nothing new reaches the backend: this feature produces a string that the
existing path field could have produced by typing.

## Dependencies

- **17-image-input-source** — the contract a dropped path feeds, unchanged.

## Security

The path comes from the OS drag payload, not from page content, and lands in a field the
user could have typed. No new endpoint and no new backend input. The listener is torn down
on unmount, including the race where the component unmounts before the async subscription
resolves — otherwise it outlives the component and fires into a dead handler.

## Verified

**Partially, and the gap is named.** In the browser: `hasFileDrop()` is false, no drop hint
is offered on any of the three fields, and nothing else changes. Types check against the
real `DragDropEvent` union. `folderOf` is pinned by thirteen cases including Windows
separators, dotfiles, a folder with a dot in its name, and an image at the filesystem root.

**The desktop drop itself is not exercised.** It needs a human to drag a folder onto the
Tauri window; nothing available here can perform or observe that. See `known_issues`.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

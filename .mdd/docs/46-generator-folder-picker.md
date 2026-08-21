---
id: 46-generator-folder-picker
title: The Generator's Folder Picker — One Field, Three Ways In
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-7-5
wave_status: in_progress
depends_on: [40-drag-and-drop-input]
relates: [22-generator-panel, 32-studio-session-setup, 17-image-source]
source_files:
  - apps/frontend/src/components/FolderField.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/components/SessionSetup.tsx
routes: []
models: []
test_files:
  - apps/frontend/src/components/FolderField.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [dataset-generator, file-picker, tauri, dialog, drag-and-drop, react]
path: Dataset Generator/Input
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues:
  - "**The buttons exist only under Tauri.** `hasNativeDialog()` is false in the browser dev mode and in Wave 9's website build, where the field stays a typable text box. Both branches are pinned by tests, but the buttons themselves were verified only by test — the live check ran in web mode, where they correctly do not render."
  - "`ImageSourcePicker` deliberately does **not** use `FolderField`. Doc 17's viewer accepts a single image *or* a folder and means different things by each; collapsing one into the other would break it. So there are still two implementations of 'a path field with pickers', and they are two on purpose."
  - "The Studio's button was labelled **Browse…** and is now **Image… / Folder…**. Nothing referenced the old label, but a user who knew where it was has to look once."
sister_projects: []
---

# 46 — The Generator's Folder Picker

## Purpose

Give the Dataset Generator the same way in that the other tabs have.

## What "the dataset picker is not working" turned out to mean

Jan reported the Create-Dataset tab's picker as broken. **The dataset dropdown works** — it
was driven live and React state updates correctly, 16 options, selection round-trips.

The gap was next to it. A count of the picker helpers across the three surfaces:

```
ImageSourcePicker.tsx   5     Image… and Folder…
SessionSetup.tsx        4     Browse…
GeneratorSetup.tsx      0     — a bare text box
```

The Generator expected the user to type an absolute path, beside two tabs that offer a
dialog. That is the thing that was not working.

## One rule a fourth copy would have got wrong

**An image means the folder it is in.**

A user who picks or drops `photos/cat-07.jpg` is telling you where their photos are, not
asking to process one file. `folderOf` is therefore applied on *both* paths in — the drop
handler and the picker — so the field can never end up holding a file path that the backend
then rejects with an error pointing at the wrong thing.

The Generator's drop handler already did this. Its picker, had one been added inline, would
have been the fourth place to remember to. So `FolderField` owns the field, its two buttons,
its drop target and this rule, and the Studio adopted it too — gaining the **Image…** button
it had also been missing.

`ImageSourcePicker` stays as it is, and that is not an oversight: doc 17's viewer takes a
single image *or* a folder and means different things by each.

## Business Rules

1. **`hasNativeDialog()` is read in an effect, not at module scope.** It asks whether Tauri
   injected its globals, and on the first render it has not.
2. **No dialog means a typable field, never a disabled one.** Wave 9's website build has no
   native picker; disabling the field there would leave no way in at all.
3. **A dismissed dialog reports nothing.** Cancelling leaves the field as it was rather than
   blanking it.
4. **Image… comes first.** People know where a photo is more readily than they know a
   folder's name.

## Verified

Seven tests, including that a picked *image* is reported as its folder and a picked folder
passes straight through — the asymmetry that is the whole point of the component.

**Verified in the running app on 2026-08-21**: the Generator's field is the shared component
(`#gen-folder`, inside a `setup__control`). The buttons correctly do not render in web mode,
which is the branch the live check could reach.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

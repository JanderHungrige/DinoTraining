---
id: 59-reveal-dataset-folder
title: Open a Dataset's Folder — Where the Pictures Actually Are
edition: MDD
initiative: dinotraining
wave: dinotraining-wave-8
wave_status: complete
depends_on: [50-dataset-as-source, 46-generator-folder-picker]
relates: [51-library-tab, 40-drag-and-drop-input]
source_files:
  - backend/app/api/v1/datasets.py
  - apps/frontend/src/components/RevealDatasetButton.tsx
  - apps/frontend/src/components/ImageSourceField.tsx
  - apps/frontend/src/components/ImageSourcePicker.tsx
  - apps/frontend/src/components/GeneratorDestination.tsx
  - apps/frontend/src/api/datasets.ts
  - apps/frontend/src/lib/dialog.ts
  - apps/frontend/src/styles.css
  - apps/desktop/src-tauri/Cargo.toml
  - apps/desktop/src-tauri/src/lib.rs
  - apps/desktop/src-tauri/capabilities/default.json
routes:
  - GET /api/v1/datasets/{dataset_id}/folder
models: []
test_files:
  - backend/tests/test_library_routes.py
  - apps/frontend/src/components/RevealDatasetButton.test.tsx
data_flow: reads-existing
last_synced: 2026-08-21
status: complete
phase: all
mdd_version: 11
tags: [tauri, opener, datasets, file-manager, admin, desktop]
path: Annotation Studio/Input
integration_contracts: []
satisfies_contracts: []
security_read_sites:
  - backend/app/api/v1/datasets.py (returns a stored path; the caller reveals it)
known_issues:
  - "**Never clicked in the real desktop app.** The button is Tauri-only, and this session has no way to drive a native webview. It was verified by making the browser report itself as Tauri, which exercises the gating, the placement and the API call but stops short of `revealItemInDir`. `cargo check` passes with the plugin and capability, and the app starts with no permission errors — that is as far as the evidence goes."
  - "**Not in the Library tab.** That lists datasets rather than selecting one, and the ask was about selection. It is the obvious next place and each row already knows its id."
  - "The folder comes from the *first* image. A dataset whose images span several directories — perfectly legal for a non-copying dataset — opens the first one and says nothing about the others."
  - "`revealItemInDir` on a directory selects it in its parent rather than opening it. That is the correct behaviour for revealing a file and slightly odd for a folder; `openPath` would open it but can reuse a window the user was reading something else in."
sister_projects: []
---

# 59 — Open a Dataset's Folder

## Purpose

> "Wherever you select to choose an existing dataset, add a button to open the folder."

A dataset is an abstraction over files the user still owns. At some point they want the
files — to back them up, to add more, or to check that the thing they picked is the thing
they meant.

## Which folder is not obvious

The tempting implementation derives the path from the dataset id: `<store>/<id>/images/`.
It is wrong for half the datasets in the app.

Every dataset gets that directory at creation, but it only *contains* anything when the
dataset was created with `copy_images`. A dataset that references the user's own files
leaves it empty — so the button would open an empty folder and tell them their pictures
are not there.

`GET /datasets/{id}/folder` derives it from the **first stored image path** instead, which
is correct for both kinds, and falls back to the dataset's own directory when there are no
images at all — a button that opens nothing is worse than one that opens the manifest.

It also reports `exists`, because **"the folder is gone" and "the button is broken" must
not look the same.** An original the user moved leaves the boxes in the store and the path
pointing at nothing; the button says which folder is missing rather than failing silently.

## Where it appears

Three places, which is what "wherever" meant:

| surface | the selection it sits beside |
|---|---|
| Annotation Studio / Dataset Generator | *"A dataset you already have"* — where the images come from |
| Inference Viewer | *"…or a dataset you already have"* |
| Dataset Generator | *"Save into"* — where results are written |

The last one is a dataset selection too. "Where does this go" is worth opening as often as
"where did this come from".

## Business Rules

1. **Tauri only.** There is no file manager to open in the browser dev mode or in Wave 9,
   so the button is absent — the same rule the folder pickers follow, and the reason
   `hasNativeDialog` is read in an effect rather than at module scope.
2. **Absent when nothing is selected.** An id of `''` means no dataset, and a button that
   opens the last thing chosen would be worse than none.
3. **The error clears when the dataset changes.** *"That folder is gone"* left standing
   against a dataset the user has since switched away from reads as a fresh failure.
4. **`revealItemInDir`, not `openPath`.** Revealing opens a new file-manager window with
   the item selected; opening a directory can reuse a window the user was reading something
   else in.

## Verified

10 frontend tests and 5 backend, including that the endpoint points at the images rather
than the store directory, and that a moved original reports `exists: false`.

**Verified in the running app on 2026-08-21** by making the browser report itself as Tauri
— which exercises the gating, the placement and the API call, and stops short of the OS
call. The Studio shows one button, the Generator two (source and destination), the Viewer
one once a dataset is chosen, and none of them before. `cargo check` passes with the plugin
and the capability, and the desktop app starts with no permission errors.

**It has never been clicked in the real app**, and that is the gap: this session cannot
drive a native webview.

## Known Issues

See frontmatter.

## Bugs

(none yet — populated by /mdd bug when issues are reported)

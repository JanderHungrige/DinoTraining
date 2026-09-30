---
id: 69-remembered-entries
title: Remembered Entries
edition: DinoTraining
depends_on: []
relates: [46-generator-folder-picker, 50-dataset-as-source]
source_files:
  - apps/frontend/src/hooks/usePersistentState.ts
  - apps/frontend/src/lib/persisted.ts
  - apps/frontend/src/hooks/useGeneratorEntries.ts
  - apps/frontend/src/hooks/useGeneratorCatalogue.ts
  - apps/frontend/src/hooks/useStudioEntries.ts
  - apps/frontend/src/components/ImageSourceField.tsx
  - apps/frontend/src/components/SessionSetup.tsx
  - apps/frontend/src/components/GeneratorSetup.tsx
  - apps/frontend/src/components/PrescanPanel.tsx
  - apps/frontend/src/components/FinetunePanel.tsx
  - apps/frontend/src/components/HeadImportForm.tsx
  - apps/frontend/src/components/SequencePanel.tsx
  - apps/frontend/src/tabs/InferenceViewerTab.tsx
  - apps/frontend/src/tabs/HeadTrainerTab.tsx
  - apps/frontend/src/tabs/DatasetGeneratorTab.tsx
  - apps/frontend/src/test-setup.ts
routes: []
models: []
test_files:
  - apps/frontend/src/hooks/usePersistentState.test.ts
  - apps/frontend/src/lib/persisted.test.ts
  - apps/frontend/src/components/GeneratorSetup.remembered.test.tsx
  - apps/frontend/src/components/TokenPanel.test.tsx
data_flow: reads-existing
last_synced: 2026-09-29
status: complete
phase: all
mdd_version: 11
tags: [persistence, local-storage, forms, react-state, tabs, usability]
path: App Shell/Remembered Entries
initiative: dinotraining
wave: dinotraining-wave-9
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "A remembered dataset *source* (ImageSourceField) whose dataset was deleted falls back to the first usable dataset once the list loads. If no dataset has images at all, the stale id stays and Start reports the backend's 'not found' rather than disabling. That is a narrow case, and clearing the id there would also clear it while the list is merely loading."
  - "Verification surfaced a pre-existing backend hazard, not introduced here: /inference/source opens the image on the event loop, so a macOS privacy prompt (a fresh Python process asking for ~/Downloads) blocks every other request, /health included, until the prompt is answered. The UI shows 'Loading heads…' indefinitely." 
security_read_sites: []
sister_projects: []
---

# 69 — Remembered Entries

## Purpose

Reported as: *"For all the path, names etc. entries. Remember all the entries. They are
always gone when changing tabs."* True, and structural: `App.tsx` renders only the active
tab, so every other tab is unmounted and every `useState` in it is dropped. Nothing is
persisted anywhere; `localStorage` is used nowhere in the frontend.

Jan chose **"also after a restart"**. So entries go to `localStorage`, which covers both
a tab switch and an app restart with one mechanism.

## Architecture

```
usePersistentState(key, initial, guard)      hooks/usePersistentState.ts
   │  lazy read on first render (synchronous, so this is not "seeding from async")
   │  write on every change, inside try/catch
   ▼
lib/persisted.ts
   readPersisted / writePersisted            namespaced "dinotraining.v1.<key>"
   guards: isString, isNumber, isOneOf, isStringArray, isImageSource, isShapeOf(defaults)
   stillListed(id, ids)                      a remembered id that is no longer offered → ''
```

`usePersistentState` has the same signature as `useState` plus a key and a guard. A call
site swaps one for the other, and nothing else about the component changes.

## Business Rules

1. **Every read goes through a guard.** A stored value can be from an older build, edited by
   hand, or truncated. If it fails the guard, the default is used, never the bad value.
   Shaped objects (`TrainerSelection`) use `isShapeOf(DEFAULTS)`: every default key must be
   present with the same `typeof`, and arrays must stay arrays. A value that fails is
   dropped whole rather than partially merged, because half a remembered form looks
   complete and is not.
2. **Storage failing is never an error to the user.** Private windows, full quotas and
   disabled storage all throw. Reads fall back to the default, writes are dropped, and one
   `console.warn` is logged with the key. The form still works exactly as before this doc.
3. **A remembered id is an override, never a seed.** This is CLAUDE.md's React-state rule
   with one addition. The dataset, head or detector may have been deleted since it was
   remembered. So the effective value is `stillListed(override, ids) || ids[0] || ''`.
   While the list is still loading, `ids` is empty and the effective value is `''`. That is
   the same as today before the fetch resolves, and it corrects itself when the list
   arrives. The remembered override is kept rather than cleared, so a list that briefly
   fails to load does not erase it.
4. **Remembered id lists are filtered on use** (`datasetIds` in training and fine-tuning).
   A deleted dataset is dropped from what is *submitted*, but not from storage.
5. **What is remembered:** image source folder or dataset, proposal or generator mode,
   prompts and concepts, new dataset names, destination dataset, model overrides
   (detector, head, backbone, annotator), score thresholds, prescan labels and threshold,
   the Inference Viewer's mode, path, dataset and view, the sequence count and fps, the
   training selection and mode, the fine-tune name and settings, and the head-import repo id.
6. **What is never remembered:**
   - **The HF token draft** (`TokenPanel`). It is a secret, and `localStorage` is plain
     text on disk. CLAUDE.md: never persist or print tokens.
   - **Running sessions and jobs** (the Generator's current image, a training run). This
     doc keeps entries only. A session that survives a tab switch is a different feature
     with different failure modes.
   - **Transient UI state** (open/closed panels, busy flags, errors).
7. **Keys are per surface.** `PrescanPanel` appears in the Studio and the Generator. It
   takes a `storageKey` prop, so a Studio label list never shows up in the Generator.
8. **Tests start empty.** `test-setup.ts` clears `localStorage` after every test. Without
   that, an earlier test's typed folder silently pre-fills the next test's form.

## Data Flow

User types → setter from `usePersistentState` → React state (render) + `localStorage`
write. On mount → `localStorage` read → guard → initial state. No backend involvement.

## Dependencies

None. The `stillListed` rule is doc 50's (dataset as source) and doc 46's (folder picker)
overrides, extended to survive a restart.

## Security

- **Stored:** folder paths, dataset names, prompts and ids. All are local and user-typed,
  and none is a secret. They are stored in the webview's origin storage on this machine only.
- **Explicitly excluded:** the HF token (rule 6). A test asserts that `TokenPanel` does not
  write to storage.
- **Input trust:** stored values are untrusted on read. They are guarded (rule 1), and a
  remembered path goes through the same backend routes and checks as a typed one. Nothing
  is executed or interpolated into HTML.

## Verified in the running app (2026-09-29)

- Typed a folder, a concept and a new dataset name in the Generator with Grounded SAM
  selected. They were written under `dinotraining.v1.generator.*`.
- Switched to Library, confirmed the Generator form had unmounted, and switched back. All
  four entries and the mode radio were back.
- Reloaded the page, which is what a restart does to the webview's JS state. The entries
  were back and **Start generating** was enabled, so the derived values resolved against
  the freshly loaded lists.
- Typed an image path in the Inference Viewer, switched away and back. The viewer re-issued
  `GET /inference/source?path=<remembered path>` on its own.

## Known Issues

## Bugs

- **2026-09-29 — Start lost the remembered dataset and kept the name, so the next Start
  created a duplicate dataset.** Found while verifying doc 70 in the running app: two
  datasets called "Wave 9 action bar check". The first version wrote to `localStorage`
  *inside* the `setState` updater. React runs the first update on an idle component
  eagerly, but a second update in the same event is queued, and a queued updater runs only
  when the component renders again. Start sets the dataset, clears the name, and unmounts
  the setup form, so it never rendered again and the second write was dropped.
  - **Fix:** write when the setter is called, keeping a ref of the latest value so two
    updaters in one event still compose.
  - **Test:** two setters on one component, then an unmount in the same `act`. A single
    setter passes against the bug because of the eager path, which is why the first test
    missed it.
  - **Verified live:** Start, then Change setup. The new dataset was selected and the name
    was cleared. Start again produced no second dataset.

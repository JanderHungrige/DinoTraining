---
id: 112-frontend-strings
title: Frontend Strings — Every Visible Text through the Catalogue, in English and German
edition: DinoTraining
depends_on: [111-i18n-framework]
relates: [114-german-translation, 113-backend-texts]
source_files:
  - apps/frontend/src/i18n/en/*.ts
  - apps/frontend/src/i18n/de/*.ts
  - apps/frontend/src/i18n/catalogue.ts
  - apps/frontend/src (every component, hook and lib with visible text)
routes: []
models: []
test_files:
  - apps/frontend/src/i18n/catalogue.test.ts
  - apps/frontend/src/i18n/german.test.tsx
data_flow: reads-existing
last_synced: 2026-09-30
status: in_progress
phase: all
mdd_version: 11
tags: [i18n, german, english, frontend, strings]
path: App/Language/Strings
initiative: dinotraining
wave: dinotraining-wave-15
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 112 — Frontend Strings

## Purpose

Every text a user can see or hear moves into doc 111's catalogue, in English (unchanged)
and German. That covers labels, buttons, hints, headings, `aria-label`s, `title`s,
placeholders, status and error messages written by the frontend, and the intro. Doc 114
(the German) is done in the same pass, by the same hands, with the glossary below.

## Namespaces and who owns them

The work is split by area. Each area has one namespace file per language, and only its
own component files:

| Namespace | Files |
|---|---|
| `app` | TabBar, tabs.ts, BackendStatus, api/client.ts messages, types/annotation.ts (verdict names), types/annotationView.ts, FieldHint, StubPanel, MarkdownView, AppearancePanel, BackgroundVideo, lib/dragDrop, hooks/useFileDrop |
| `intro` | IntroTab, introContent.ts, datasetFormat.ts, DatasetFormatPanel |
| `studio` | the Studio: tab, setup, canvas, lists, pickers, image sources, prescan, target guide, outline tools, their hooks and libs |
| `phrases` | phrases/*, GuidelinePanel, SecondLook, usePicturePhrases, useSecondLook |
| `prepare` | PrepareTab, prepare/*, usePrepareData, usePreparePlans |
| `training` | HeadTrainerTab, TrainerForm, TrainingProgress, Recipe*, params/*, finetune/*, HeadInstanceList, their hooks, api/parameters.ts, api/training.ts, api/heads.ts, api/headInstances.ts texts |
| `run` | InferenceViewerTab, SideBySideViewer, VideoPlayer, SequencePanel, overlays/*, HeadRunPanel, StoredOverlay, MaskSourceFields, TilingField, Frame/Mask canvases, their hooks, api/videoExtract.ts |
| `generator` | DatasetGeneratorTab, Generator*, Autoplay*, Unclear*, their hooks and libs; InspectTab, AnnotationTimeline, DatasetPlayer, useInspectData, usePlayback, lib/timeline |
| `admin` | LibraryTab, useLibrary, AdminTab, ModelCard, ModelGuidePanel, StarterSetPanel, TokenPanel, GpuPanel, DistributionNotice, HeadCatalog*, HeadImportForm, useHeadCatalog, useModels, ApiTab, McpPanel |

## Rules for moving a text

1. **Keys** are `<ns>.<area>.<what>` in camelCase, e.g. `studio.setup.startButton`.
2. **The English value is the current text, exactly.** Every existing test reads English
   and must pass unchanged. A test may only be edited where a function's signature changed
   (a translator parameter).
3. **Components** call `const { t, tp } = useT()` from `../i18n` (the path adjusted).
   **Hooks** do the same. **Pure functions** (`lib/*`, module constants) take a
   `Translator` parameter, or return keys that the component translates. Default the
   parameter to `ENGLISH` only where many callers exist.
4. **Module-level constant tables** of UI text (tab labels, option lists) keep their
   structure but hold keys, and are translated where rendered.
5. **Placeholders** use `{name}`. **Plurals** use `…_one` / `…_other` with `tp()`, never
   a hand-written `s`.
6. **Not translated:**
   - model ids and names (RF-DETR, SAM 3, DINOv2, Grounding DINO), file paths, code,
     JSON keys, CSS classes, `data-testid`s;
   - text that comes from the backend (doc 113 translates that);
   - log and `console` messages.
7. **Every file stays ≤ 300 lines.** A namespace file that would exceed it splits into
   `<ns>2.ts`, registered by the lead.

## Verification

- tsc clean, and every test green.
- The catalogue test from doc 111 (parity, no untranslated values, placeholders kept).
- A German smoke test (`german.test.tsx`) renders each tab inside a German provider and
  asserts that key texts read German.
- Checked in the running app in German, at the pane's narrow width.

## Bugs

(none yet)

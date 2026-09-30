---
id: 114-german-translation
title: German Translation — One Glossary, Informal "du", Checked for Completeness and Consistency
edition: DinoTraining
depends_on: [112-frontend-strings, 113-backend-texts]
relates: [111-i18n-framework]
source_files:
  - apps/frontend/src/i18n/GLOSSARY.md
  - apps/frontend/src/i18n/de/*.ts
  - backend/app/i18n/de_*.py
routes: []
models: []
test_files:
  - apps/frontend/src/i18n/catalogue.test.ts
  - apps/frontend/src/i18n/*.german.test.tsx
  - backend/tests/test_i18n_coverage.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [i18n, german, glossary, translation, non-experts]
path: App/Language/German
initiative: dinotraining
wave: dinotraining-wave-15
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "The glossary's word choices were made in the build, not yet reviewed by Jan (see 'For Jan to review')."
security_read_sites: []
sister_projects: []
---

# 114 — German Translation

## Purpose

The German has to read as clearly as the English, for people who have never trained a
model, and use **one word per concept** across the UI and the backend's answers.

## How consistency was kept

- **`GLOSSARY.md` is the single source.**
  - It fixes informal **du**, and about 50 terms. Examples: Bild, Datensatz, Umriss (Maske),
    Klasse, Phrase, Variante, Rezept, Aufteilung (Training / Validierung / Test), Durchgang
    (Epochen), Lerngeschwindigkeit (Lernrate), Basismodell, Kachel, Befund, veränderte
    Kopien, harte Negativbeispiele, Richtlinie, Zweiter Blick, Einzelbild.
  - Tab names: Hier starten, Daten vorbereiten, Modell-Ansicht, Datensatz-Generator,
    Datensätze ansehen, Bibliothek, Verwaltung / Modelle, Verbindung.
- **Everyone read it:** all ten builders used it, the nine frontend namespaces and the
  backend catalogue. The backend reused the frontend's step names, so a finding says
  "Ungleiche Klassen" exactly where the tab does.
- **Kept as they are:**
  - product and model names;
  - "Annotation Studio", "Training", "Test", "Prompt", "Backbone", "Head" (allow-listed);
  - concepts typed *to* a model stay English examples, and the German hints say so,
    because Grounding DINO and SAM read English.

## Completeness, enforced

- **Frontend:**
  - A missing key is a compile error.
  - `catalogue.test.ts` fails an untranslated value or a lost placeholder.
  - Each namespace has a German smoke test.
- **Backend:** the coverage tests of doc 113.

## For Jan to review

These are judgement calls from the build:
- "optional" (badge) → *freiwillig*;
- "clear" → *zurücksetzen*;
- "Pause" → *Anhalten*;
- "Stop" → *Stopp*;
- "gated" → *zugangsbeschränkt*;
- "Prescan" → *Vorab-Suche*;
- the "problem" severity → *Fehler*;
- "Original" in the augmentation strip → *Ausgangsbild*;
- the head's one-time explanation, *"kleine Modelle auf dem Backbone"*.

## Bugs

(none yet)

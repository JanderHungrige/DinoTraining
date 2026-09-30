---
id: 111-i18n-framework
title: i18n Framework — A Typed Catalogue, a Language Switch, and the Language Sent to the Backend
edition: DinoTraining
depends_on: [69-remembered-entries]
relates: [112-frontend-strings, 113-backend-texts, 114-german-translation]
source_files:
  - apps/frontend/src/i18n/index.ts
  - apps/frontend/src/i18n/types.ts
  - apps/frontend/src/i18n/catalogue.ts
  - apps/frontend/src/i18n/translate.ts
  - apps/frontend/src/i18n/LanguageProvider.tsx
  - apps/frontend/src/i18n/useT.ts
  - apps/frontend/src/i18n/en/common.ts
  - apps/frontend/src/i18n/de/common.ts
  - apps/frontend/src/components/LanguageSwitch.tsx
  - apps/frontend/src/api/client.ts
  - apps/frontend/src/App.tsx
routes: []
models: []
test_files:
  - apps/frontend/src/i18n/i18n.test.tsx
  - apps/frontend/src/i18n/catalogue.test.ts
data_flow: greenfield
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [i18n, german, english, language, frontend, accessibility]
path: App/Language
initiative: dinotraining
wave: dinotraining-wave-15
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues: []
security_read_sites: []
sister_projects: []
---

# 111 — i18n Framework

## Purpose

Jan (2026-09-30): *"Add a language option and English."* English stays the source, and
German is added. This doc is the machinery; doc 112 moves the texts into it, doc 113 does
the backend's texts, and doc 114 makes the German complete and consistent.

## Decision: a small typed module, not react-i18next

- **What we need:**
  - lookups by key, with `{name}` placeholders;
  - plural forms (`Intl.PluralRules`);
  - one switch;
  - **a missing German text that fails the build.**
- **Why not react-i18next:** its keys are strings resolved at run time. Type-checking them
  needs generated declarations, while a TypeScript object gives it for free.
  - Per namespace, `de/<ns>.ts` is typed `Catalogue<typeof <ns>En>`: every English key,
    and nothing else. A missing German key is a compile error that names the key.
  - Also no dependency, and nothing to load: the app works offline.

## Architecture

- **`i18n/en/<ns>.ts`:** `export const <ns>En = { '<ns>.<key>': 'English', … } as const`.
  Keys are fully qualified, so namespaces merge without collisions.
- **`i18n/de/<ns>.ts`:** `export const <ns>De: Catalogue<typeof <ns>En> = { … }`.
- **`catalogue.ts`:** merges every namespace into `en` and `de`. `Key` is the union of all
  keys.
- **`translate(lang, key, params)`** interpolates `{name}`. A missing key falls back to
  English (this cannot happen while the types hold).
- **Plurals:** `translatePlural(lang, key, count, params)` picks `key_one` / `key_other` by
  `Intl.PluralRules(lang)`, with `{count}` filled in.
- **`LanguageProvider`:**
  - holds the language, remembered (doc 69 key `language`);
  - defaults to the OS/browser language (`de*` → German, anything else English);
  - sets `<html lang>`, and tells the API client (below).
- **`useT()`** returns `{ t, tp, lang }`. Outside a provider it is English, so every existing
  test that renders a component bare keeps reading English.
- **`LanguageSwitch`** sits in the header: a labelled select, "English" / "Deutsch" (each in
  its own language, so a user who cannot read the current one still finds theirs). Admin
  links to it.
- **API client:** every request sends `Accept-Language` with the current language, so the
  backend can answer in it (doc 113). MCP's internal calls send none and get English.

## Code that is not a component

A pure function that makes text (`pictureChecklist`, `figure`, `problemWith`) takes the
translator as a parameter (`tr: Translator`). A hook calls `useT()` itself.

## Business Rules

1. **English is the source:** every key exists in English first.
2. **A German value identical to the English one fails a test,** unless allow-listed
   (proper names such as "RF-DETR", and "OK"-like words).
3. **Model ids, file paths and technical identifiers are never translated.**

## Verified (2026-09-30)

- **Tests:** frontend 1041 green; tsc clean.
- **What the tests check:**
  - the catalogue test: German keys equal English keys, no untranslated values, every
    placeholder kept;
  - plural forms in both languages;
  - the provider: follows `navigator.language`; the switch changes texts, `<html lang>`
    and the API language; the choice is remembered.
- **Running app:** the switch sits in the header between the title and the backend status,
  and `<html lang>` is "en" in the English-language browser pane.

## Bugs

(none yet)

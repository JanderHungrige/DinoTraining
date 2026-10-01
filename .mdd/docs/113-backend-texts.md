---
id: 113-backend-texts
title: Backend Texts — The Plain-Language Answers in German, Chosen by Accept-Language
edition: DinoTraining
depends_on: [111-i18n-framework, 81-dataset-audit, 92-data-requirements-contract, 99-parameter-catalogue, 104-annotation-target]
relates: [112-frontend-strings, 114-german-translation]
source_files:
  - backend/app/i18n/__init__.py
  - backend/app/i18n/translate.py
  - backend/app/i18n/middleware.py
  - backend/app/i18n/de_*.py
  - backend/app/main.py
routes: []
models: []
test_files:
  - backend/tests/test_i18n.py
  - backend/tests/test_i18n_coverage.py
  - backend/tests/test_dataset_format_guide.py
data_flow: reads-existing
last_synced: 2026-09-30
status: complete
phase: all
mdd_version: 11
tags: [i18n, german, backend, audit, requirements, parameters, accept-language]
path: App/Language/Backend
initiative: dinotraining
wave: dinotraining-wave-15
wave_status: complete
integration_contracts: []
satisfies_contracts: []
known_issues:
  - "A stored text is translated only if its English still matches a catalogue template. An audit saved before a rule's wording changed (e.g. 'unchecked-pictures' before the per-phrase amendment) keeps those sentences in English until it is run again."
  - "An unhandled 500 is written by Starlette's outermost layer after the middleware, so it stays English."
  - "Texts outside the covered areas pass through in English: training/video job messages, model/head/annotator descriptions, rarer 422 details."
security_read_sites: []
sister_projects: []
---

# 113 — Backend Texts

## Purpose

Much of what a non-expert reads is written by the backend:
- the audit's findings (docs 81, 107, 109);
- the data requirements and preflight refusals (doc 92);
- the parameter explanations (doc 99);
- the annotation-target matrix (doc 104);
- job messages and notes, error messages.

In German they must be German.

## Decision: English stays in the code; the answer is translated on the way out

**Why not keys in the code:** replacing every English string in the backend with a key
would touch every rule. It would also break two things that must stay English: the MCP
tools' answers (their reader is a language model, doc 110) and the stored audits
(`audit.json`), which were written in English and would stay English forever.

**Instead:**
- **`app/i18n/translate.py`:**
  - A catalogue of **templates**: the English text with `{name}` where it varies, beside
    its German.
  - Static texts are looked up exactly.
  - Varying ones are matched by a regular expression compiled from the template. The
    captured values (numbers, class names, paths) are put into the German unchanged.
- **`app/i18n/middleware.py`:**
  - For a JSON response to a request whose `Accept-Language` starts with `de`, it walks
    the body and translates the strings under **text fields**: `title`, `what`, `why`,
    `action`, `help`, `label`, `term`, `summary`, `message`, `detail`, `fix`,
    `data_format`, `notes`, `warnings`, `reason`, …
  - It never translates ids, paths or keys.
  - Streaming responses pass through untouched.
- **The error envelope's `message`** is a text field too, so refusals (422/409) arrive in
  German.
- **MCP's internal calls** send no `Accept-Language` and get English.
- **The catalogue** lives in `app/i18n/de_<area>.py` modules (audit, requirements,
  parameters, targets, jobs), each ≤ 300 lines. It follows `apps/frontend/src/i18n/
  GLOSSARY.md`, the same terms as the UI.

## Business Rules

1. **An unmatched text passes through in English:** never an error, never an empty
   string.
2. **Captured values are not translated.** A class name stays the user's word.
3. **Coverage is tested:**
   - Every text of the static catalogues (requirements, parameters, targets, profiles) is
     translated. A test compares the English and German responses field by field.
   - The audit test builds contexts that fire every rule and asserts each finding's
     title, what, why and action are German.

## Built (2026-09-30)

- **`translate.py`:**
  - Exact texts first. Varying texts are anchored templates, bucketed by their first
    characters, with the longest literal tried first.
  - **Placeholder kinds:**
    - `{x}`: a value kept as is;
    - `{#x}`: a number;
    - `{+x}`: English prose, translated too (e.g. a model label);
    - `{*x}`: prose that may span sentences.
  - **Assembled messages** (the preflight refusal) are translated sentence by sentence,
    then by "title: detail".
- **`middleware.py`:**
  - Pure ASGI. Only `/api/v1`, only JSON, only `Accept-Language: de*`; SSE is never
    buffered.
  - Adds `Vary: Accept-Language` and fixes `Content-Length`. A body it cannot parse is sent
    in English, with a warning.
- **Catalogue:** 9 modules, 475 entries (audit, audit per task, requirements, parameters,
  SAM parameters, targets, prep, jobs, errors). The wording is the glossary's, with the
  frontend's step names.
- **Coverage tests:**
  - The four static endpoints compared field by field, German vs English. Non-text fields
    must be identical.
  - Contexts that fire all 20 audit rules; the test compares with `len(RULES)`, so a new
    rule fails it until it has German.
  - All 6 intake findings.
- **MCP stays English:** a test runs the real MCP client call and gets the English 404.
- **The dataset-format guide test** (doc 48) now reads the prose from the English catalogue,
  and checks that the German keeps the category-0 warning and the box convention.

## Verified (2026-09-30)

- **Tests:** backend 1813 green; ruff and mypy (226 files) are clean.
- **Running app, German:**
  - The Studio's target matrix read "Alle Möglichkeiten offenhalten — … Empfohlen.",
    "Begriffs-Umrisse (SAM 3) — Jedes Vorkommen jeder Phrase umrissen und jedes Bild
    geprüft."
  - A fresh SAM 3 audit read German in every title/what/why/action.
  - A 404 read *"Datensatz nicht gefunden: nope"*.
  - The same audit without the header stayed English.

## Bugs

(none yet)

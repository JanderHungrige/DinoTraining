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
data_flow: reads-existing
last_synced: 2026-09-30
status: in_progress
phase: all
mdd_version: 11
tags: [i18n, german, backend, audit, requirements, parameters, accept-language]
path: App/Language/Backend
initiative: dinotraining
wave: dinotraining-wave-15
wave_status: active
integration_contracts: []
satisfies_contracts: []
known_issues: []
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

## Bugs

(none yet)

---
id: dinotraining-wave-15
title: "Wave 15: English and German"
initiative: dinotraining
initiative_version: 12
status: planned
depends_on: dinotraining-wave-14
demo_state: "The user switches the language in the header; every text of the app — tabs, forms, the ? explanations, the intro, and the backend's audit findings, requirements and preflight refusals — appears in German, and switches back to English. A missing German text fails the build, not the user."
created: 2026-09-30
hash: a30e6737
---

# Wave 15: English and German

**Jan's request (2026-09-30):**
- a language option;
- English stays the source language and German is added (confirmed);
- last of the three waves, because it touches every text the two waves before it write.

## What already exists

- **Frontend:** every text is hardcoded English, in about 64 of 91 components, plus
  `introContent.ts` (305 lines).
- **Backend:** its plain-language texts reach the UI directly:
  - audit findings (doc 81);
  - requirements and preflight (doc 92);
  - parameter help (doc 99);
  - phrase and negatives explanations (Wave 14).
- There is no i18n library.

## Decisions

- **English is the source language.** Every key exists in English first.
- **German is complete or the build fails.** A test compares the key sets, and it flags
  German values identical to English (except an allow-list, e.g. "mAP").
- **MCP tools and the agent guide stay English.** Their reader is a language model, and the
  texts are tested for content.
- **The language defaults to the OS language** and is remembered.

## Demo-State

1. **The header's language switch** sets German.
   - Tabs, forms, the ? popovers, the intro and the Generator are in German.
   - The audit findings of a dataset, a fine-tune refusal and the parameter explanations
     are in German too.
2. **Switching back** gives English, and the setting survives a restart.
3. **A build with one German key removed fails,** naming the key.

*(Not complete until this can be manually demonstrated.)*

## Features

| # | Feature | Doc | Status | Depends on |
|---|---------|-----|--------|------------|
| 1 | i18n-framework | docs/111-i18n-framework.md | complete | — |
| 2 | frontend-strings | docs/112-frontend-strings.md | complete | i18n-framework |
| 3 | backend-texts | docs/113-backend-texts.md | planned | i18n-framework |
| 4 | german-translation | docs/114-german-translation.md | planned | frontend-strings, backend-texts |

### Feature notes

1. **i18n-framework.**
   - A typed catalogue, with keys checked by TypeScript.
   - A `useT()` hook, with plural and number formatting (`Intl`).
   - The switch in the header and in Admin, and the language setting.
   - The doc decides between react-i18next and a small own module.
2. **frontend-strings.**
   - Every visible text moves to the catalogue, including `aria-label`s, titles and the
     intro.
   - A lint or test catches new hardcoded text.
3. **backend-texts.**
   - User-facing backend texts come from catalogues keyed by message id with parameters.
   - They are chosen per request by `Accept-Language`, which the frontend client sends.
   - MCP asks for English.
4. **german-translation.**
   - The complete German catalogue, using consistent terms: a glossary (Durchgang für epoch,
     Rezept for recipe, and so on), agreed with Jan.

## Open Research

- **Glossary:** which technical terms stay English in German ML practice (e.g. "Fine-Tuning",
  "Batch")? This needs Jan's call.
- **Text length:** German runs ~30 % longer. Check the toolbar and the chips at the narrow
  pane width.

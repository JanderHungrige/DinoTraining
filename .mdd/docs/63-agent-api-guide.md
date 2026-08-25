---
id: 63-agent-api-guide
title: An API Guide an Agent Can Follow — And a PDF a Person Can Read
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: in_progress
depends_on: [01-app-shell, 38-intro-tab]
relates: [44-finetune-rf-detr, 31-external-dataset-import, 48-dataset-format-guide]
source_files:
  - backend/app/docs/workflows.py
  - backend/app/docs/reference.py
  - backend/app/api/v1/agent_docs.py
  - backend/app/api/v1/router.py
  - apps/frontend/src/api/agentGuide.ts
  - apps/frontend/src/lib/markdown.ts
  - apps/frontend/src/components/MarkdownView.tsx
  - apps/frontend/src/tabs/ApiTab.tsx
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/App.tsx
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/docs/agent-guide
models: []
test_files:
  - backend/tests/test_agent_docs.py
  - apps/frontend/src/lib/markdown.test.ts
  - apps/frontend/src/tabs/ApiTab.test.tsx
data_flow: reads-existing
last_synced: 2026-08-25
status: complete
phase: all
mdd_version: 11
tags: [api, documentation, agent, openapi, markdown, pdf, automation]
path: API/Guide
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 63 — An API Guide an Agent Can Follow

## Purpose

Let someone hand their own AI assistant one document and say *"here is a dataset link —
download it, fine-tune RF-DETR on it, then generate a dataset."* Everything that request
needs already exists as an endpoint. What does not exist is the **order**.

## What was already there, and what was actually missing

The API is complete for the task and fully machine-described: **51 paths, 60 operations**,
with `/openapi.json` and Swagger UI at `/docs` both already served. Walking the requested
workflow against it, every step is covered:

```
POST /models/rf-detr-nano/download  →  GET /models/jobs/{id}          install
POST /datasets/import/coco          →  dataset_id                     ingest
POST /foundation/finetune           →  GET /foundation/finetune/{id}  train and poll
POST /generate/foundation           →  PUT /datasets/{id}/images      auto-annotate
POST /datasets/{id}/export/coco                                       ship
```

So this feature adds **no endpoints for the workflow itself**. That is the finding, and it
is worth stating plainly because the obvious reading of the request — "build an API" —
would have produced a second API beside a complete one.

**What OpenAPI cannot say** is the part an agent needs most:

* that a model must be *installed* before it can be fine-tuned, and that installing is a
  job you poll rather than a call that blocks;
* that `image_path` means an absolute path **on the machine running the backend**, because
  the sidecar reads the file itself;
* that a fine-tune is a job id and a poll loop, not a response;
* that `boxes[].prompt` is the class, and sending `text` silently lands NULL (doc 31);
* which of two similarly-named routes is the one for this job.

A schema describes shapes. A recipe describes order, preconditions and traps.

## Generated, not written twice

The endpoint reference is rendered **from the live OpenAPI schema at request time**, not
transcribed. A hand-maintained endpoint list is wrong the first time anyone adds a route
and is worse than no list, because it is confidently wrong. Only the workflows — the part
no schema can derive — are prose.

That split is the whole design: **prose for order, generation for surface.**

## Architecture

```
GET /api/v1/docs/agent-guide
  │
  ├─ workflows.py     hand-written recipes: order, preconditions, traps
  ├─ reference.py     renders request.app.openapi() to markdown
  └─ joined           → one markdown document, text/markdown

Frontend (API tab)
  ├─ Copy for your AI     clipboard  ← the actual primary action
  ├─ Download .md         a file the agent can be handed
  └─ Save as PDF          window.print() + a print stylesheet
```

## Why Markdown is the real deliverable, and PDF is the courtesy

The request asked for PDF. It is included, and it is the *worse* format for the stated
purpose: an LLM given a PDF has to have it extracted first, and layout becomes noise.
Markdown is what these models are trained to read, and "Copy for your AI" is therefore the
primary button rather than the download.

**PDF is produced by `window.print()` against a print stylesheet**, not by a generator on
the backend. Adding `weasyprint` or `reportlab` to the sidecar would be the wrong trade
against doc 56: it is already 636 MB frozen, and the installers are 181–377 MB. The browser
already has a PDF writer and the OS print dialog is a better one than we would ship.

## Business Rules

1. **The endpoint reference is generated at request time**, so it cannot go stale. Adding a
   route to `router.py` puts it in the guide with no other edit.
2. **The workflows are hand-written and versioned as code**, because they encode decisions —
   which of two routes, what to poll, what a field means — that no schema records.
3. **Every recipe is a numbered sequence with real calls**, not a description of one. An
   agent follows steps; it does not infer them from prose.
4. **The base URL is stated, and stated as loopback.** The single most likely agent failure
   is calling a public host. `127.0.0.1:8756` and *why* it is local is the first thing in
   the document.
5. **Paths are the backend's, not the agent's.** A recipe that says "upload the image" would
   be wrong: every image route takes an absolute path the sidecar opens itself.
6. **Traps are documented beside the step they trap.** Doc 31's `text`-versus-`prompt` bug
   cost a whole wave's datasets their classes; a guide that omits it invites it back.

## API

### `GET /api/v1/docs/agent-guide`

Returns the whole guide as `text/markdown; charset=utf-8`.

* `?format=md` (default) — markdown.
* No auth, same as every other route: this backend is loopback-only by design.

Deliberately **one document**, not a document per workflow: the caller is pasting it into a
context window, and five fetches to assemble one prompt is five ways to send half of it.

## Data Flow

Read-only, and reads only the app's own description of itself:

```
FastAPI app  →  request.app.openapi()  →  reference.py  ─┐
                                                          ├→ markdown → response
workflows.py (module constants) ─────────────────────────┘
```

Nothing touches the database, the filesystem or a model.

## Dependencies

* `01-app-shell` — the FastAPI app whose schema is the source of the reference half.
* `38-intro-tab` — the precedent for docs as a tab, and for prose living in a content
  module rather than inside JSX.

## Security

The route reads the app's own OpenAPI schema and hand-written constants. It takes no input
beyond an enum-validated `format`, touches no file, and runs no model.

Worth noting what the *guide* does rather than what the route does: it tells a reader that
this API has **no authentication** and takes absolute local paths. That is already true and
already discoverable at `/docs`; writing it down does not widen the surface, and a user
pointing an agent at the API needs to understand it. The CORS allowlist and loopback
binding remain the actual controls.

## Verified

**In the running app on 2026-08-25.** The guide is **13.2 KB** — comfortably pasteable —
with 7 code blocks and every one of the app's 52 paths present. The three actions work:
copy (confirmed via a stubbed clipboard, and it admits refusal rather than pretending),
download, and print.

The generated half is checked against the live schema rather than a fixture, so
`test_every_route_the_app_serves_appears` fails the moment a route is added without the
guide following.

**A first look in the browser caught a real bug the tests had not**: the guide writes bold
sentences with paths in them — *"The API is at `http://127.0.0.1:8756/api/v1` and only
there."* — and the parser rendered those backticks literally. The parser's own docstring had
claimed the generator never emits code inside bold, which was simply wrong about a document
I had written an hour earlier. `MarkdownView` re-parses a bold span now; it terminates
because the bold pattern excludes `*`. After: 25 bold runs, **0** showing literal backticks,
5 rendering code.

## Known Issues

- "**`window.print()` is unverified in the packaged app.** It works in the dev browser; WKWebView
  is a different question and this project has been caught by that difference twice already
  (doc 61). The Markdown paths do not depend on it, and they are the ones that matter for
  the stated use."
- "**The reference does not resolve `$ref` bodies.** Most request bodies are refs, so the
  *(requires: …)* hint appears only for the inlined ones. Following refs would make this a
  schema walker, and the guide points at `/openapi.json`, which already is one."
- "**The workflows can drift from the app.** The endpoint list cannot — it is generated — but
  a recipe that says "poll until `state != running`" is prose, and a change to job semantics
  would not fail a test. The tests assert the *traps* are present, not that they are still
  true."
- "**No auth, stated plainly.** The guide tells a reader this API has none and takes absolute
  local paths. That was already true and already at `/docs`; writing it down does not widen
  the surface, but it does make it easier to find."
- "**One language.** The guide is English only, and an assistant working in another language
  gets English instructions. Fine in practice — these models translate — but worth naming."

## Bugs

(none yet — populated by /mdd bug when issues are reported)

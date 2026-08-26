---
id: 64-mcp-server
title: An MCP Server — Typed Tools Instead of a Document to Interpret
edition: MDD
initiative: dinotraining
wave: unassigned
wave_status: complete
depends_on: [63-agent-api-guide, 01-app-shell]
relates: [44-finetune-rf-detr, 62-tiled-inference, 31-external-dataset-import]
source_files:
  - backend/app/mcp/client.py
  - backend/app/mcp/tools.py
  - backend/app/mcp/server.py
  - backend/app/api/v1/agent_docs.py
  - backend/app/main.py
  - backend/pyproject.toml
  - apps/frontend/src/api/mcpInfo.ts
  - apps/frontend/src/components/McpPanel.tsx
  - apps/frontend/src/tabs/ApiTab.tsx
  - apps/frontend/src/tabs/tabs.ts
  - apps/frontend/src/styles.css
routes:
  - GET /api/v1/docs/mcp
  - POST /mcp
models: []
test_files:
  - backend/tests/test_mcp_server.py
  - apps/frontend/src/components/McpPanel.test.tsx
  - apps/frontend/src/tabs/ApiTab.test.tsx
data_flow: reads-existing
last_synced: 2026-08-26
status: complete
phase: all
mdd_version: 11
tags: [mcp, agent, automation, api, tools, local-assistant]
path: Connection/MCP
integration_contracts: []
satisfies_contracts: []
security_read_sites: []
known_issues: []
sister_projects: []
---

# 64 — An MCP Server

## Purpose

Doc 63 gave an assistant a document to read. This gives it **tools to call** — typed, with
the preconditions in the schema, so it cannot invent a parameter or forget that a model has
to be installed before it can be fine-tuned.

## Mounted on the sidecar, not shipped beside it

The server runs **inside the FastAPI process that already runs**, at `/mcp`. Nothing to
install, nothing to launch, and it is up whenever the app is. A standalone stdio server was
the alternative and would have re-solved the packaging problem Wave 8 already solved: where
does the script live, what Python runs it, and how does it get into a frozen bundle.

## The spike, and why it earned its keep

The transport was spiked before anything was designed around it — the same call made for
Private Network Access in the backlog. Five findings, and **four of the five fail at request
time rather than at startup**, which is the worst possible shape for a bug:

| finding | how it fails |
|---|---|
| `mcp` 2.x renamed `FastMCP` to `MCPServer` | import error — the only honest one |
| path and security are kwargs to `streamable_http_app()`, not constructor settings | silently ignored |
| DNS-rebinding protection is **on by default** | `421`, never mentioning an allowlist |
| a mounted sub-app's lifespan is **not** run by FastAPI | `Task group is not initialized`, long after startup looked fine |
| `stateless_http=True` removes the session handshake | `Bad Request: Missing session ID` |

A sixth was found by the test suite rather than the spike: the sub-app routes its own path,
so mounting it at `/mcp` serves the endpoint from `/mcp/mcp`. Mounting at `""` fixes the URL
and creates a worse problem — **an empty mount prefix matches everything**, so it becomes a
catch-all at the end of the route table and silently kills every route registered after it.
Two `test_health.py` tests caught exactly that. The arrangement that is both correct and
contained is to root the sub-app at `/` and mount it at `/mcp`.

## Tools call the API, not the store

A tool dispatches into the app's **own HTTP routes, in-process**, through
`httpx.ASGITransport`.

Not by importing `DatasetStore`: this project has a single shared connection module so that
one process owns the SQLite file, and a tool layer with its own connection would be a second
owner with its own idea of when a transaction ends.

Not over a real socket either: `ASGITransport` needs no port, no DNS and no assumption about
what the sidecar is bound to, and it runs the full route stack — validation, the error
handlers, the `ValueError → 422` backstops. A tool therefore cannot behave differently from
the endpoint it wraps. It is what `datasets_api_testkit.py` already does.

## Fifteen tools, not sixty-one

Task-shaped, not endpoint-shaped. The API has 61 operations and exposing one tool each would
flood the model's context and leave it orchestrating anyway — the problem doc 63 exists to
solve.

**Every docstring is the prompt.** A client shows the model the name, the description and
the parameter types, and nothing else, before it decides. So the preconditions and the traps
live in the docstrings: `save_annotations` says the class field is `prompt` and that sending
`text` is silently dropped (doc 31); `run_inference` says a tile-trained head finds nothing
on a full frame *and the call still succeeds* (doc 62). A test asserts both are still there.

**Long work is never awaited.** Downloads, training and fine-tuning return a job id and
`get_job` polls it, with `kind` as an enum so the model cannot invent a fourth job type.
Blocking a tool call for four minutes hits a client timeout and loses the run.

## Business Rules

1. **The tool list and the setup command are generated, never transcribed.**
   `GET /docs/mcp` reads the live server and the bound settings, so the Connection tab
   cannot show a stale list or a wrong URL — the same rule doc 63's endpoint reference
   follows.
2. **A failure is raised, not returned.** A dict with an `error` key is as likely to be
   summarised as success; a raised error makes the client mark the call failed and show the
   API's own message, which is written for a person and names the fix.
3. **The allowlist is built from the configured bind address**, never widened until a
   request works. DNS rebinding is a real attack on a local HTTP server.
4. **MCP is the default mode of the Connection tab**, because it is the better path and the
   one that needs finding. The manual document is one click away rather than buried — the
   mistake that hid fine-tuning for three waves.

## Security

The server is bound to loopback and has **no authentication**, exactly like the REST API it
wraps, and the tools can read any absolute path they are given. That is defensible only
because it is unreachable from off-machine, so the tab says so in a bordered note rather
than a dim aside, and two tests assert that wording survives.

DNS-rebinding protection is what stops a page the user visits from resolving a name it
controls to `127.0.0.1` and driving the tools; a test asserts a foreign `Host` gets a 421.

Setting `DINO_API_HOST=0.0.0.0` would expose an unauthenticated tool server with filesystem
reach to the network. That was already true of the REST API and is now worse.

## Verified

**In the running app on 2026-08-26.** All 15 tools list over real HTTP with typed schemas,
enums and defaults; `list_heads` called through the protocol returned the ten real heads
with their `trained_width`. The Connection tab renders all 15 from the live server, and both
modes show exactly one panel at a time.

## Known Issues

- "**Local only, and that is the whole shape of it.** An assistant on this machine can use
  these tools; one anywhere else cannot. Remote access needs authentication and path
  confinement first — the hosted-GUI entry in the backlog."
- "**No progress notifications.** MCP supports them; jobs are poll-only here because that is
  what the REST API already does and what the guide already teaches. A long fine-tune is
  silent between polls."
- "**Untested against a real MCP client.** Every test drives the JSON-RPC endpoint directly,
  which is the protocol a client speaks — but no actual Claude Code session has connected,
  and the `claude mcp add` command is written rather than executed."
- "**The tools are not in the frozen sidecar's build yet.** `mcp` is declared in
  `pyproject.toml`; whether PyInstaller picks it up cleanly is a doc 56 question nobody has
  asked."

## Bugs

(none yet — populated by /mdd bug when issues are reported)
